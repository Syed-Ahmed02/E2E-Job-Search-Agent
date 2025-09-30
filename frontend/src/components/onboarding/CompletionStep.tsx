'use client'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CheckCircle } from 'lucide-react'

interface CompletionStepProps {
  onComplete: () => void
  userName?: string
}

export function CompletionStep({ onComplete, userName }: CompletionStepProps) {
  return (
    <Card className="w-full max-w-md mx-auto p-6">
      <div className="space-y-6 text-center">
        <div className="flex justify-center">
          <CheckCircle className="h-16 w-16 text-green-500" />
        </div>
        
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">
            Welcome{userName ? `, ${userName}` : ''}!
          </h2>
          <p className="text-muted-foreground">
            Your profile has been set up successfully. You're all ready to start your job search journey!
          </p>
        </div>

        <div className="space-y-3 text-left bg-muted/50 p-4 rounded-lg">
          <h3 className="font-semibold">What's next?</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              Upload your resume to get started
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              Browse job opportunities
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              Get personalized job recommendations
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              Track your applications
            </li>
          </ul>
        </div>

        <Button onClick={onComplete} className="w-full">
          Get Started
        </Button>
      </div>
    </Card>
  )
}
