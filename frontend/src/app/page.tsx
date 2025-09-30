import { Hero } from "@/components/Hero";
import { FeatureSection } from "@/components/FeatureSection";
import { auth } from "@clerk/nextjs/server";
import { createUserMessage, deleteUserMessage, getUserMessages } from "@/actions/actions";

export default async function Home() {
  const { isAuthenticated, userId } = await auth()
  if (!isAuthenticated) throw new Error('User not found')
  
  const messages = await getUserMessages()
  
  return (
    <div >
      <Hero />
      <FeatureSection />
      <main>
        <h1>Neon + Clerk Example</h1>
        
        {/* Add new message form */}
        <form action={createUserMessage}>
          <input type="text" name="message" placeholder="Enter a message" />
          <button>Save Message</button>
        </form>
        
        {/* Display all messages */}
        {messages.length > 0 && (
          <div>
            <h2>Your Messages:</h2>
            {messages.map((message) => (
              <div key={message.id} style={{ border: '1px solid #ccc', padding: '10px', margin: '10px 0' }}>
                <p>{message.message}</p>
                <p><small>Created: {message.createTs?.toLocaleString()}</small></p>
                <form action={deleteUserMessage}>
                  <input type="hidden" name="messageId" value={message.id} />
                  <button type="submit">Delete Message</button>
                </form>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
