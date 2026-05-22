/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  experimental: {
    esmExternals: "loose",
  },
};

module.exports = nextConfig;
