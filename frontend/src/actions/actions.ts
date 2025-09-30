'use server'

import { auth } from '@clerk/nextjs/server'
import { UserMessages } from '@/db/schema'
import { db } from '@/db'
import { eq, and } from 'drizzle-orm'

export async function createUserMessage(formData: FormData) {
  const { isAuthenticated, userId } = await auth()
  if (!isAuthenticated) throw new Error('User not found')

  const message = formData.get('message') as string
  await db.insert(UserMessages).values({
    user_id: userId,
    message,
  })
}

export async function deleteUserMessage(formData: FormData) {
  const { isAuthenticated, userId } = await auth()
  if (!isAuthenticated) throw new Error('User not found')

  const messageId = parseInt(formData.get('messageId') as string)
  await db.delete(UserMessages).where(
    and(eq(UserMessages.id, messageId), eq(UserMessages.user_id, userId))
  )
}

export async function getUserMessages() {
  const { isAuthenticated, userId } = await auth()
  if (!isAuthenticated) throw new Error('User not found')

  return await db.select().from(UserMessages).where(eq(UserMessages.user_id, userId))
}