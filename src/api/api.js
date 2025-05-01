export const getAIMessage = async (userQuery) => {
  try {
    const res = await fetch(`${process.env.REACT_APP_API_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message: userQuery })
    });

    const data = await res.json();

    return {
      role: "assistant",
      content: data.reply || "⚠️ No response received from backend."
    };
  } catch (err) {
    console.error("API error:", err);
    return {
      role: "assistant",
      content: "⚠️ Backend is not responding. Please check the server."
    };
  }
};

