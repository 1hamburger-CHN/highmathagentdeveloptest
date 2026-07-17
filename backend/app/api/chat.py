"""Chat API — SSE streaming and non-streaming endpoints with profile persistence."""
import json
import logging
import traceback
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import build_tutor_graph
from app.agents.state import AgentState, TutorState
from app.core.safety import SafetyPipeline
from app.models.db_models import upsert_session, upsert_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_pending_out_of_domain_concept(messages: list[dict]) -> str:
    """Check if last assistant message is an out-of-domain asking message.

    Pattern: '<concept> 不在当前复变函数知识范围内，需要我帮你搜索并生成相关内容吗？'
    """
    if not messages:
        return ""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if "不在当前复变函数知识范围内" in content and "需要我帮你搜索并生成相关内容吗" in content:
                return content.split(" 不在当前复变函数知识范围内")[0].strip()
            return ""
    return ""

# Build the LangGraph graph once at module level
_tutor_graph = build_tutor_graph()

# Intermediate agents that work silently — their messages are hidden from user
_SILENT_NODES = {"build_profile", "diagnose"}


def _save_profile_and_session(user_id: str, session_id: str, profile: dict, messages: list[dict]):
    """Persist profile and session messages to Turso."""
    try:
        upsert_user(user_id, json.dumps(profile, ensure_ascii=False))
        upsert_session(session_id, user_id, json.dumps(messages, ensure_ascii=False))
        logger.info(f"Saved profile+session for user={user_id} session={session_id}")
    except Exception as e:
        logger.error(f"Failed to save profile+session for {user_id}: {e}")


@router.post("/stream")
async def chat_stream(payload: dict):
    """SSE streaming endpoint. Runs the full LangGraph tutoring pipeline."""
    user_message = payload.get("message", "")
    image_data = payload.get("image", "")  # base64 image data
    session_id = payload.get("session_id", uuid4().hex)
    user_id = payload.get("user_id", "anonymous")
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

    # --- Image understanding: call Spark Image API first ---
    if image_data and user_message:
        async def image_stream_generator():
            yield {"event": "start", "data": json.dumps({"session_id": session_id})}
            yield {"event": "node", "data": json.dumps({"node": "image_analysis"})}

            # Call Spark Image API
            from app.core.spark_image import spark_image_chat
            analysis = await spark_image_chat(image_data, user_message)
            logger.info(f"Image analysis result: {analysis[:100]}...")

            yield {
                "event": "message",
                "data": json.dumps({
                    "role": "assistant",
                    "content": f"图片分析结果：\n\n{analysis}\n\n正在基于图片内容进行辅导...",
                    "node": "image_analysis",
                }, ensure_ascii=False),
            }

            # Feed analysis into normal coaching pipeline
            inner_prompt = f"学生上传了一张图片，图片内容分析如下：\n\n{analysis}\n\n学生的原始问题是：{user_message}\n\n请基于图片内容进行苏格拉底式辅导。"
            inner_transcript = history + [{"role": "user", "content": user_message}]
            inner_transcript.append({"role": "assistant", "content": f"图片分析结果：{analysis}"})
            accumulated = existing_profile

            async for event in _tutor_graph.astream(
                TutorState(
                    session_id=session_id,
                    user_id=user_id,
                    current_state=AgentState.INIT,
                    messages=inner_transcript,
                    profile=existing_profile,
                ),
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    yield {"event": "node", "data": json.dumps({"node": node_name})}
                    if isinstance(node_output, dict):
                        if node_output.get("profile"):
                            accumulated = node_output["profile"]
                        msgs = node_output.get("messages", [])
                        for msg in msgs:
                            content = msg.get("content", "")
                            if content:
                                inner_transcript.append({"role": "assistant", "content": content})
                                yield {
                                    "event": "message",
                                    "data": json.dumps({
                                        "role": msg.get("role", "assistant"),
                                        "content": content,
                                        "node": node_name,
                                    }, ensure_ascii=False),
                                }

            _save_profile_and_session(user_id, session_id, accumulated or {}, inner_transcript)
            yield {"event": "done", "data": json.dumps({"status": "complete", "session_id": session_id, "profile": accumulated})}

        return EventSourceResponse(image_stream_generator())

    # Belt-and-suspenders: safety check at endpoint level
    last_assistant_msg = ""
    for m in reversed(history):
        if m.get("role") in ("assistant", "coach"):
            last_assistant_msg = m.get("content", "")
            break
    safety_result = SafetyPipeline.filter(user_message, last_assistant_msg)
    if not safety_result["allowed"]:
        async def rejected_generator():
            yield {"event": "start", "data": json.dumps({"session_id": session_id})}
            yield {"event": "message", "data": json.dumps({"role": "assistant", "content": safety_result["content"], "node": "safety_check"}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"status": "complete", "session_id": session_id})}
        return EventSourceResponse(rejected_generator())

    # Build message list: history + current message
    # We'll append assistant responses during streaming, then save the full transcript
    full_transcript: list[dict] = history + [{"role": "user", "content": user_message}]

    initial_state = TutorState(
        session_id=session_id,
        user_id=user_id,
        current_state=AgentState.INIT,
        messages=list(full_transcript),
        profile=existing_profile,
    )

    # Restore pending out-of-domain concept from previous turn
    _pending = _extract_pending_out_of_domain_concept(full_transcript)
    if _pending:
        initial_state._pending_out_of_domain_concept = _pending

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"session_id": session_id})}

        try:
            accumulated_profile = existing_profile
            last_node_output = None
            async for event in _tutor_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    yield {"event": "node", "data": json.dumps({"node": node_name})}

                    if isinstance(node_output, dict):
                        if node_output.get("profile"):
                            accumulated_profile = node_output["profile"]
                            # Emit profile progress after profile is updated
                            km = accumulated_profile.get("knowledge_mastery", [])
                            assessed = [c for c in km if c.get("score", 0) > 0]
                            yield {
                                "event": "profile_progress",
                                "data": json.dumps({
                                    "assessed": len(assessed),
                                    "total_concepts": 17,
                                    "concepts": [{
                                        "id": c["concept_id"],
                                        "score": c["score"],
                                    } for c in assessed],
                                }),
                            }

                        if node_name not in _SILENT_NODES:
                            msgs = node_output.get("messages", [])
                            for msg in msgs:
                                content = msg.get("content", "")
                                role = msg.get("role", "assistant")
                                plaintext = msg.get("plaintext", False)
                                full_transcript.append({"role": role, "content": content})
                                yield {
                                    "event": "message",
                                    "data": json.dumps({
                                        "role": role,
                                        "content": content,
                                        "node": node_name,
                                        "plaintext": plaintext,
                                    }, ensure_ascii=False),
                                }
                        if node_output.get("assessment_result"):
                            yield {
                                "event": "assessment",
                                "data": json.dumps(node_output["assessment_result"], ensure_ascii=False),
                            }
                        if node_output.get("generated_resources"):
                            yield {
                                "event": "resources",
                                "data": json.dumps(node_output["generated_resources"], ensure_ascii=False),
                            }
                        if node_output.get("sources"):
                            yield {
                                "event": "reference",
                                "data": json.dumps({"sources": node_output["sources"]}, ensure_ascii=False),
                            }
                    last_node_output = node_output

            yield {
                "event": "done",
                "data": json.dumps({
                    "status": "complete",
                    "session_id": session_id,
                    "profile": accumulated_profile,
                }, ensure_ascii=False),
            }

        except Exception as e:
            logger.error(f"Chat stream error (session={session_id}): {type(e).__name__}: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            yield {"event": "error", "data": json.dumps({"message": "服务暂时不可用，请稍后重试"})}
        finally:
            # Always persist — even if the stream errored, save what we have
            _save_profile_and_session(user_id, session_id, accumulated_profile or {}, full_transcript)

    return EventSourceResponse(event_generator())


@router.post("/send")
async def chat_send(payload: dict):
    """Non-streaming endpoint: send a message and get the full response."""
    user_message = payload.get("message", "")
    user_id = payload.get("user_id", "anonymous")
    session_id = payload.get("session_id", uuid4().hex)
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

    safety_result = SafetyPipeline.filter(user_message)
    if not safety_result["allowed"]:
        return {
            "messages": [{"role": "assistant", "content": safety_result["content"]}],
            "rejected": True,
            "reason": safety_result["reason"],
        }

    full_transcript = history + [{"role": "user", "content": user_message}]

    initial_state = TutorState(
        session_id=session_id,
        user_id=user_id,
        current_state=AgentState.INIT,
        messages=list(full_transcript),
        profile=existing_profile,
    )

    _pending = _extract_pending_out_of_domain_concept(full_transcript)
    if _pending:
        initial_state._pending_out_of_domain_concept = _pending

    try:
        final_state = await _tutor_graph.ainvoke(initial_state)
        updated_profile = final_state.get("profile", existing_profile)

        # Collect the full transcript including assistant responses
        result_messages = final_state.get("messages", [])
        full_transcript.extend(
            {"role": m.get("role", "assistant"), "content": m.get("content", "")}
            for m in result_messages[len(full_transcript):]
        )
        _save_profile_and_session(user_id, session_id, updated_profile or {}, full_transcript)

        return {
            "messages": result_messages,
            "profile": updated_profile,
            "session_id": session_id,
            "assessment": final_state.get("assessment_result"),
            "resources": final_state.get("generated_resources"),
        }
    except Exception as e:
        logger.error(f"Chat send error (user={user_id}): {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")
