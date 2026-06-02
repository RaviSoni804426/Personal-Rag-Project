/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  // Ensure that links do not crash when exported statically
  trailingSlash: true,
}

module.exports = nextConfig
