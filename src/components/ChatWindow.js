import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { getAIMessage } from "../api/api";
import "./ChatWindow.css";

const initialOptions = [
  "Check Order Status",
  "Return an Order",
  "Cancel an Order",
  "Search for a refrigerator part",
  "Search for a dishwasher part",
  "Is this part compatible with my model?",
  "How do I install a replacement part?"
];

function ChatWindow() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm here to help with any questions you have about refrigerator or dishwasher parts. Let me know what you need assistance with!\n\nIf you're looking for repair help, check out these official repair guides:\n\n- [Refrigerator](https://www.partselect.com/Repair/Refrigerator/)\n- [Dishwasher](https://www.partselect.com/Repair/Dishwasher/)"
    }
  ]);
  const [input, setInput] = useState("");
  const [buttonsVisible, setButtonsVisible] = useState(true);
  const [thinking, setThinking] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    if (hasInteracted) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text) => {
    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setHasInteracted(true);
    if (buttonsVisible) setButtonsVisible(false);
    setThinking(true);

    const aiResponse = await getAIMessage(text);
    setMessages((prev) => [...prev, aiResponse]);
    setInput("");
    setThinking(false);
  };

  const handleQuickAction = (actionText) => {
    handleSend(actionText);
  };

  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`${msg.role}-message`}>
            <ReactMarkdown
              components={{
                a: (props) => (
                  <a href={props.href} target="_blank" rel="noopener noreferrer">
                    {props.children}
                  </a>
                ),
              }}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        ))}

        {thinking && (
          <div className="assistant-message-container">
            <div className="assistant-message thinking-placeholder">
              <div className="robot-thinking">
                🤖
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {buttonsVisible && (
        <div className="quick-actions">
          {initialOptions.map((text, idx) => (
            <button key={idx} onClick={() => handleQuickAction(text)}>
              {text}
            </button>
          ))}
        </div>
      )}

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && input.trim() && handleSend(input)}
          placeholder="Type your question..."
        />
        <button onClick={() => handleSend(input)} disabled={!input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;

