// 从环境变量获取端口，默认为3000
const backendPort = process.env.BACKEND_PORT || 3000;

module.exports = {
    devServer: {
        port: 8000,
        proxy: {
            "/api": {
                target: `http://localhost:${backendPort}`,
                changeOrigin: true,
            },
            "/socket.io": {
                target: `http://localhost:${backendPort}`,
                changeOrigin: true,
                ws: true,
            },
        },
    },
};
