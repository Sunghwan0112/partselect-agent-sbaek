import React from "react";
import { Layout } from "antd";
import ChatWindow from "./components/ChatWindow";
import "antd/dist/reset.css";
import "./App.css";

const { Header, Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ background: "#3E7A87", padding: "0 24px", display: "flex", alignItems: "center" }}>
        <img
          src="/logo.png"
          alt="PartSelect Logo"
          style={{ height: 40, marginRight: 16 }}
        />
        <div style={{ color: "white", fontWeight: "bold", fontSize: 18 }}>
          PartSelect Assistant
        </div>
      </Header>
      <Content style={{ padding: "24px" }}>
        <ChatWindow />
      </Content>
    </Layout>
  );
}

export default App;
