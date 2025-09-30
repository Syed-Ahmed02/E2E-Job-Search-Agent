'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { PersonalInfoStep } from './PersonalInfoStep'
import { ResumeUploadStep } from './ResumeUploadStep'
import { SkillsStep } from './SkillsStep'
import { CompletionStep } from './CompletionStep'
import { updateProfileClient, updateUserSkillsClient, getProfileClient } from '@/lib/database/client'
import { createClient } from '@/lib/supabase/client'

interface OnboardingData {
  personalInfo?: {
    full_name: string
    phone_number: string
    linkedin_url: string
  }
  skills?: Array<{
    skill_id: string
    proficiency_level: string
  }>
}

export function OnboardingFlow() {
  const [currentStep, setCurrentStep] = useState(1)
  const [onboardingData, setOnboardingData] = useState<OnboardingData>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const router = useRouter()

  const totalSteps = 4

  const handlePersonalInfoNext = async (data: {
    full_name: string
    phone_number: string
    linkedin_url: string
  }) => {
    setLoading(true)
    setError('')

    try {
      // Update profile with personal information
      await updateProfileClient({
        full_name: data.full_name,
        phone_number: data.phone_number,
        linkedin_url: data.linkedin_url
      })

      setOnboardingData(prev => ({ ...prev, personalInfo: data }))
      setCurrentStep(2)
    } catch (err) {
      setError('Failed to save personal information. Please try again.')
      console.error('Error saving personal info:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleResumeUploadNext = () => {
    setCurrentStep(3)
  }

  const handleSkillsNext = async (skills: Array<{
    skill_id: string
    proficiency_level: string
  }>) => {
    setLoading(true)
    setError('')

    try {
      // Update user skills
      await updateUserSkillsClient(skills)

      setOnboardingData(prev => ({ ...prev, skills }))
      setCurrentStep(4)
    } catch (err) {
      setError('Failed to save skills. Please try again.')
      console.error('Error saving skills:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async () => {
    setLoading(true)
    setError('')

    try {
      // Mark onboarding as completed
      await updateProfileClient({
        onboarding_completed: true
      })

      // Redirect to the main app
      router.push('/protected')
    } catch (err) {
      setError('Failed to complete onboarding. Please try again.')
      console.error('Error completing onboarding:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <PersonalInfoStep
            onNext={handlePersonalInfoNext}
            initialData={onboardingData.personalInfo}
          />
        )
      case 2:
        return (
          <ResumeUploadStep
            onNext={handleResumeUploadNext}
            onBack={handleBack}
          />
        )
      case 3:
        return (
          <SkillsStep
            onNext={handleSkillsNext}
            onBack={handleBack}
            initialSkills={onboardingData.skills}
          />
        )
      case 4:
        return (
          <CompletionStep
            onComplete={handleComplete}
            userName={onboardingData.personalInfo?.full_name}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex space-x-2">
              {Array.from({ length: totalSteps }, (_, index) => (
                <div
                  key={index}
                  className={`w-3 h-3 rounded-full transition-colors ${
                    index + 1 <= currentStep
                      ? 'bg-blue-500'
                      : 'bg-gray-300 dark:bg-gray-600'
                  }`}
                />
              ))}
            </div>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Step {currentStep} of {totalSteps}
            </p>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-center">
            {error}
          </div>
        )}

        {/* Loading Overlay */}
        {loading && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg">
              <p>Processing...</p>
            </div>
          </div>
        )}

        {/* Step Content */}
        {renderStep()}
      </div>
    </div>
  )
}
