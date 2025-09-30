'use client'

import { useState, useTransition } from 'react'
import { createRecord, updateRecord, deleteRecord } from '@/actions/database'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function ExampleForm() {
  const [isPending, startTransition] = useTransition()
  const [formData, setFormData] = useState({
    title: '',
    description: ''
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    startTransition(async () => {
      const result = await createRecord(formData)
      
      if (result.status === 'success') {
        // Reset form on success
        setFormData({ title: '', description: '' })
        // The page will automatically revalidate due to revalidatePath in the action
      } else {
        // Handle error (you might want to show a toast notification)
        console.error(result.message)
      }
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          value={formData.title}
          onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
          required
        />
      </div>
      
      <div>
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          required
        />
      </div>
      
      <Button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Record'}
      </Button>
    </form>
  )
}
