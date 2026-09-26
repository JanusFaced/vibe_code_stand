import { useEffect, useRef, useState } from "react";
import {
    HeroSection,
    Container,
    Title,
    AuthorTagline,
    ChatWindow,
    MessageGroup,
    MessageRole,
    MessageBody,
    MessageLine,
    ControlBar,
    ControlButton,
    InputBar,
    Input,
    SendButton,
    StatusDot,
    StatusBar,
} from "./MainPageApp.styles.jsx";

const API = process.env.REACT_APP_API_URL;

const ROLE_LABELS = {
    user: "Вы",
    agent: "Агент",
    system: "Система",
    error: "Ошибка",
};

function groupMessages(list) {
    const grouped = [];
    for (const msg of list) {
        const last = grouped[grouped.length - 1];
        if (last && last.role === msg.role) {
            last.lines.push(msg.content);
        } else {
            grouped.push({ role: msg.role, lines: [msg.content], id: msg.id });
        }
    }
    return grouped;
}

export default function MainPageApp() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [connected, setConnected] = useState(true);
    const [running, setRunning] = useState([]);   // ← какие процессы сейчас живут
    const lastId = useRef(0);
    const chatRef = useRef(null);

    // Polling сообщений
    useEffect(() => {
        const tick = async () => {
            try {
                const r = await fetch(`${API}/api/messages?after=${lastId.current}`);
                if (!r.ok) throw new Error();
                const data = await r.json();
                setConnected(true);
                if (data.messages.length) {
                    lastId.current = data.messages[data.messages.length - 1].id;
                    setMessages((m) => [...m, ...data.messages]);
                }
            } catch {
                setConnected(false);
            }
        };
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, []);

    // Polling статуса процессов (каждые 2 секунды)
    useEffect(() => {
        const tick = async () => {
            try {
                const r = await fetch(`${API}/api/status`);
                if (!r.ok) return;
                const data = await r.json();
                setRunning(data.running || []);
            } catch {
                /* ignore */
            }
        };
        tick();
        const id = setInterval(tick, 2000);
        return () => clearInterval(id);
    }, []);

    // Автоскролл
    useEffect(() => {
        if (chatRef.current) {
            chatRef.current.scrollTop = chatRef.current.scrollHeight;
        }
    }, [messages.length]);

    const send = async (text) => {
        const trimmed = text.trim();
        if (!trimmed) return;
        setInput("");
        try {
            await fetch(`${API}/api/command`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: trimmed }),
            });
        } catch {
            setConnected(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        send(input);
    };

    const handleControl = (command) => send(command);

    const grouped = groupMessages(messages);

    return (
        <HeroSection>
            <Container>
                <Title>AI Agent</Title>
                <AuthorTagline>vibe-coding console</AuthorTagline>

                <StatusBar>
                    <StatusDot $online={connected} />
                    {connected ? "online" : "offline"}
                    {running.length > 0 && ` · running: ${running.join(", ")}`}
                </StatusBar>

                <ControlBar>
                    <ControlButton onClick={() => handleControl("/start")}>
                        ▶ start project
                    </ControlButton>
                    <ControlButton onClick={() => handleControl("/stop project")}>
                        ⏹ stop project
                    </ControlButton>
                    <ControlButton onClick={() => handleControl("/stop vibecoding")}>
                        ⏹ stop vibecoding
                    </ControlButton>
                    <ControlButton onClick={() => handleControl("/status")}>
                        ● status
                    </ControlButton>
                    <ControlButton onClick={() => handleControl("/clear")}>
                        ⌫ clear
                    </ControlButton>
                </ControlBar>

                <ChatWindow ref={chatRef}>
                    {grouped.length === 0 && (
                        <MessageLine style={{ color: "#64748b" }}>
                            Введи /task для запуска агента, /start для запуска проекта.
                        </MessageLine>
                    )}

                    {grouped.map((group) => (
                        <MessageGroup key={group.id} $role={group.role}>
                            <MessageRole $role={group.role}>
                                {ROLE_LABELS[group.role] ?? group.role}
                            </MessageRole>
                            <MessageBody>
                                {group.lines.map((line, i) => (
                                    <MessageLine key={i}>{line}</MessageLine>
                                ))}
                            </MessageBody>
                        </MessageGroup>
                    ))}
                </ChatWindow>

                <InputBar onSubmit={handleSubmit}>
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="/task текст задачи | /start | /stop project | /stop vibecoding | /status | /clear"
                    />
                    <SendButton type="submit">→</SendButton>
                </InputBar>
            </Container>
        </HeroSection>
    );
}