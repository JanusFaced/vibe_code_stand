import styled, { keyframes } from "styled-components";

const fadeInUp = keyframes`
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
`;

const pulse = keyframes`
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.35; }
`;

// ───────── Фон / секция ─────────
export const HeroSection = styled.section`
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    padding: 60px 20px;

    background:
        radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.1), transparent 32%),
        radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.08), transparent 32%),
        #0b0f19;

    color: #f8fafc;

    &::before {
        content: '';
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(148, 163, 184, 0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 163, 184, 0.035) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.5), transparent 80%);
        pointer-events: none;
    }
`;

// ───────── Контейнер ─────────
export const Container = styled.div`
    position: relative;
    z-index: 1;
    width: min(960px, 100%);
    margin: 0 auto;
    text-align: center;
`;

export const Title = styled.h1`
    margin: 0 0 0.5rem;
    color: #f8fafc;
    font-size: clamp(2rem, 5vw, 3rem);
    font-weight: 750;
    letter-spacing: -0.04em;
    text-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    animation: ${fadeInUp} 0.6s ease both;
`;

export const AuthorTagline = styled.p`
    margin: 0 0 1.5rem;
    color: #60a5fa;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    animation: ${fadeInUp} 0.6s ease 0.1s both;
`;

// ───────── Статус ─────────
export const StatusBar = styled.div`
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.85rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.6);
    color: #94a3b8;
    font-size: 0.85rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
`;

export const StatusDot = styled.span`
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${({ $online }) => ($online ? "#22c55e" : "#ef4444")};
    box-shadow: 0 0 10px ${({ $online }) => ($online ? "#22c55e" : "#ef4444")};
    animation: ${pulse} 2s ease-in-out infinite;
`;

// ───────── Панель управления ─────────
export const ControlBar = styled.div`
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
`;

export const ControlButton = styled.button`
    padding: 0.5rem 0.95rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.6);
    color: #cbd5e1;
    font-size: 0.85rem;
    font-family: ui-monospace, monospace;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
        border-color: rgba(96, 165, 250, 0.55);
        background: rgba(37, 99, 235, 0.15);
        color: #93c5fd;
        transform: translateY(-2px);
    }

    &:active { transform: translateY(0); }
`;

// ───────── Чат ─────────
export const ChatWindow = styled.div`
    height: 60vh;
    min-height: 340px;
    padding: 1.25rem;
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 14px;
    background: rgba(2, 6, 23, 0.65);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
    overflow-y: auto;
    text-align: left;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.9rem;
    line-height: 1.55;
    animation: ${fadeInUp} 0.6s ease 0.2s both;
    scrollbar-width: thin;
    scrollbar-color: rgba(96, 165, 250, 0.4) transparent;

    &::-webkit-scrollbar { width: 8px; }
    &::-webkit-scrollbar-thumb {
        background: rgba(96, 165, 250, 0.35);
        border-radius: 4px;
    }
`;

// ───────── Группа сообщений ─────────
export const MessageGroup = styled.div`
    margin-bottom: 1rem;
    padding-left: 0.75rem;
    border-left: 2px solid
        ${({ $role }) =>
            $role === "user"
                ? "#3b82f6"
                : $role === "agent"
                ? "#a78bfa"
                : $role === "error"
                ? "#ef4444"
                : "#475569"};
`;

export const MessageRole = styled.div`
    margin-bottom: 0.35rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: ${({ $role }) =>
        $role === "user"
            ? "#60a5fa"
            : $role === "agent"
            ? "#a78bfa"
            : $role === "error"
            ? "#f87171"
            : "#94a3b8"};
`;

export const MessageBody = styled.div`
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
`;

export const MessageLine = styled.div`
    white-space: pre-wrap;
    word-break: break-word;
    color: ${({ $role }) => ($role === "system" ? "#94a3b8" : "#e2e8f0")};
`;

// ───────── Инпут ─────────
export const InputBar = styled.form`
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    animation: ${fadeInUp} 0.6s ease 0.3s both;
`;

export const Input = styled.input`
    flex: 1;
    padding: 0.85rem 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.7);
    color: #f8fafc;
    font-size: 0.95rem;
    font-family: ui-monospace, monospace;
    outline: none;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;

    &::placeholder { color: #475569; }

    &:focus {
        border-color: rgba(96, 165, 250, 0.65);
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.12);
    }
`;

export const SendButton = styled.button`
    padding: 0.85rem 1.35rem;
    border: 1px solid rgba(96, 165, 250, 0.8);
    border-radius: 10px;
    background: #2563eb;
    color: #eff6ff;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
        background: #3b82f6;
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.3);
    }

    &:active { transform: translateY(0); }
`;