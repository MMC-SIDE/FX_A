/** @type {import('next').NextConfig} */
const nextConfig = {
  // 本番環境用のスタンドアロン出力設定
  output: 'standalone',
  
  // 実験的機能の設定
  experimental: {
    // サーバーサイドコンポーネントで外部パッケージを最適化
    serverComponentsExternalPackages: ['@prisma/client'],
  },
  
  // 画像最適化設定
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.fx-trading.local',
        port: '',
        pathname: '/static/**',
      },
    ],
  },
  
  // API リライト設定（本番環境用）
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'https://api.fx-trading.local/api/v1/:path*',
      },
    ]
  },
  
  // セキュリティヘッダー
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ]
  },
  
  // パフォーマンス最適化
  poweredByHeader: false,
  compress: true,
  
  // 環境変数の設定
  env: {
    NEXT_PUBLIC_APP_NAME: 'FX Trading System',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
  },
}

module.exports = nextConfig