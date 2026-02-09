package websocket;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.util.Set;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ConcurrentHashMap;

import javax.websocket.OnClose;
import javax.websocket.OnError;
import javax.websocket.OnMessage;
import javax.websocket.OnOpen;
import javax.websocket.Session;
import javax.websocket.server.ServerEndpoint;

@ServerEndpoint(value = "/numberws")
public class NumberWebSocket {
    // 存储所有WebSocket会话
    private static final Set<Session> sessions = ConcurrentHashMap.newKeySet();
    private Session session;
    private WebSocket pythonWebSocket;
    private volatile boolean isConnected = false;

    @OnOpen
    public void onOpen(Session session) {
        this.session = session;
        sessions.add(session);
        System.out.println("WebSocket已打开，sessionId: " + session.getId());
        System.out.println("当前连接数: " + sessions.size());
        connectToPython();
    }

    private void connectToPython() {
        try {
            System.out.println("开始连接Python服务器...");
            HttpClient client = HttpClient.newHttpClient();
            WebSocket.Builder builder = client.newWebSocketBuilder();
            
            System.out.println("正在连接Python服务器...");
            pythonWebSocket = builder.buildAsync(URI.create("ws://localhost:8765"), new WebSocket.Listener() {
                @Override
                public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
                    System.out.println("从Python服务器收到消息: " + data);
                    if ("pong".equals(data.toString())) {
                        System.out.println("收到Python服务器心跳响应");
                        return WebSocket.Listener.super.onText(webSocket, data, last);
                    }
                    
                    broadcastMessage(data.toString());
                    return WebSocket.Listener.super.onText(webSocket, data, last);
                }

                @Override
                public void onOpen(WebSocket webSocket) {
                    System.out.println("Python WebSocket连接已建立");
                    isConnected = true;
                    WebSocket.Listener.super.onOpen(webSocket);
                }

                @Override
                public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
                    System.out.println("Python WebSocket连接关闭 - 状态码: " + statusCode + ", 原因: " + reason);
                    isConnected = false;
                    return WebSocket.Listener.super.onClose(webSocket, statusCode, reason);
                }

                @Override
                public void onError(WebSocket webSocket, Throwable error) {
                    System.err.println("Python WebSocket连接错误: " + error.getMessage());
                    error.printStackTrace();
                    WebSocket.Listener.super.onError(webSocket, error);
                }
            }).join();
        } catch (Exception e) {
            System.err.println("连接Python服务器失败: " + e.getMessage());
            e.printStackTrace();
            if (!isConnected) {
                System.out.println("启动重连机制...");
                new Thread(() -> {
                    try {
                        Thread.sleep(5000);
                        System.out.println("尝试重新连接Python服务器...");
                        connectToPython();
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        System.err.println("重连被中断");
                    }
                }).start();
            }
        }
    }

    // 广播消息给所有连接的客户端
    private void broadcastMessage(String message) {
        System.out.println("广播消息: " + message);
        for (Session s : sessions) {
            try {
                if (s.isOpen()) {
                    s.getBasicRemote().sendText(message);
                    System.out.println("消息已发送到会话: " + s.getId());
                }
            } catch (IOException e) {
                System.err.println("发送消息到会话 " + s.getId() + " 失败: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }

    @OnMessage(maxMessageSize = 2097152)
    public void onMessage(String message, Session session) {
        System.out.println("收到消息大小: " + message.length() + " bytes");
        System.out.println("消息类型: " + (message.startsWith("{") ? "WebRTC信令" : 
                          message.startsWith("data:image") ? "图像数据" : 
                          message.equals("ping") ? "心跳" : "其他"));
        
        if (message.startsWith("{")) {  // 处理 WebRTC 信令消息
            try {
                System.out.println("处理WebRTC信令消息: " + message);
                // 转发 WebRTC 信令消息给所有其他客户端
                for (Session s : sessions) {
                    if (s.isOpen() && !s.equals(session)) {
                        s.getBasicRemote().sendText(message);
                        System.out.println("信令消息已转发到会话: " + s.getId());
                    }
                }
                return;
            } catch (IOException e) {
                System.err.println("转发信令消息失败: " + e.getMessage());
                sendErrorMessage(session, "转发信令消息失败: " + e.getMessage());
                return;
            }
        }
        
        if (!isConnected) {
            System.err.println("Python服务器未连接，消息被丢弃");
            sendErrorMessage(session, "Python服务器未连接");
            return;
        }

        try {
            if ("ping".equals(message)) {
                System.out.println("收到心跳请求");
                session.getBasicRemote().sendText("pong");
                System.out.println("已发送心跳响应");
                return;
            }

            if (message.startsWith("data:image")) {
                System.out.println("准备发送图像数据到Python服务器");
                pythonWebSocket.sendText(message, true)
                    .exceptionally(throwable -> {
                        System.err.println("发送数据到Python服务器失败: " + throwable.getMessage());
                        throwable.printStackTrace();
                        sendErrorMessage(session, "发送数据失败: " + throwable.getMessage());
                        return null;
                    });
                System.out.println("图像数据已发送到Python服务器");
            }
        } catch (Exception e) {
            System.err.println("处理消息时发生异常: " + e.getMessage());
            e.printStackTrace();
            sendErrorMessage(session, "处理消息失败: " + e.getMessage());
        }
    }

    private void sendErrorMessage(Session session, String message) {
        try {
            session.getBasicRemote().sendText("错误：" + message);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    @OnClose
    public void onClose(Session session) {
        sessions.remove(session);
        System.out.println("WebSocket已关闭，sessionId: " + session.getId());
        System.out.println("当前连接数: " + sessions.size());
        if (pythonWebSocket != null) {
            try {
                pythonWebSocket.sendClose(WebSocket.NORMAL_CLOSURE, "Client disconnected");
            } catch (Exception e) {
                System.err.println("关闭Python WebSocket连接失败: " + e.getMessage());
            } finally {
                pythonWebSocket.abort();
            }
        }
    }

    @OnError
    public void onError(Throwable error, Session session) {
        System.err.println("WebSocket错误 - Session ID: " + session.getId());
        System.err.println("错误类型: " + error.getClass().getName());
        System.err.println("错误消息: " + error.getMessage());
        error.printStackTrace();
    }
} 