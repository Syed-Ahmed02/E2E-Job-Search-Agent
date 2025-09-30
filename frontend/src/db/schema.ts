import { pgTable, text, timestamp, serial } from 'drizzle-orm/pg-core'

export const UserMessages = pgTable('user_messages', {
  id: serial('id').primaryKey(),
  user_id: text('user_id').notNull(),
  createTs: timestamp('create_ts').defaultNow().notNull(),
  message: text('message').notNull(),
})