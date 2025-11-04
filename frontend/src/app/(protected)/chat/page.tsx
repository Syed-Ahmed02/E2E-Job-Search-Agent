import { ChatClient } from "@/components/chat-client";

export default function ChatPage() {
  return (
    <div className="flex flex-col h-screen w-full">
      <div className="flex-1 overflow-hidden">
        <ChatClient />
      </div>
    </div>
  );
}

