'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { getAllSkillsClient } from '@/lib/database/client'

interface Skill {
  id: string
  name: string
  category: string
}

interface UserSkill {
  skill_id: string
  proficiency_level: string
}

interface SkillsStepProps {
  onNext: (skills: UserSkill[]) => void
  onBack: () => void
  initialSkills?: UserSkill[]
}

const PROFICIENCY_LEVELS = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'expert', label: 'Expert' }
]

export function SkillsStep({ onNext, onBack, initialSkills = [] }: SkillsStepProps) {
  const [skills, setSkills] = useState<Skill[]>([])
  const [selectedSkills, setSelectedSkills] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const hasInitialized = useRef(false)

  useEffect(() => {
    loadSkills()
  }, [])

  useEffect(() => {
    // Initialize selected skills from props only once
    if (!hasInitialized.current && initialSkills.length > 0) {
      const initialSelected = initialSkills.reduce((acc, skill) => {
        acc[skill.skill_id] = skill.proficiency_level
        return acc
      }, {} as Record<string, string>)
      setSelectedSkills(initialSelected)
      hasInitialized.current = true
    }
  }, [initialSkills])

  const loadSkills = async () => {
    try {
      const skillsData = await getAllSkillsClient()
      setSkills(skillsData)
    } catch (err) {
      setError('Failed to load skills. Please try again.')
      console.error('Error loading skills:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleSkill = (skillId: string) => {
    setSelectedSkills(prev => {
      const newSelected = { ...prev }
      if (newSelected[skillId]) {
        delete newSelected[skillId]
      } else {
        newSelected[skillId] = 'intermediate' // Default proficiency
      }
      return newSelected
    })
  }

  const updateProficiency = (skillId: string, level: string) => {
    setSelectedSkills(prev => ({
      ...prev,
      [skillId]: level
    }))
  }

  const handleNext = () => {
    const userSkills: UserSkill[] = Object.entries(selectedSkills).map(([skillId, level]) => ({
      skill_id: skillId,
      proficiency_level: level
    }))
    onNext(userSkills)
  }

  const groupedSkills = skills.reduce((acc, skill) => {
    if (!acc[skill.category]) {
      acc[skill.category] = []
    }
    acc[skill.category].push(skill)
    return acc
  }, {} as Record<string, Skill[]>)

  if (loading) {
    return (
      <Card className="w-full max-w-2xl mx-auto p-6">
        <div className="text-center">
          <p>Loading skills...</p>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="w-full max-w-2xl mx-auto p-6">
        <div className="text-center">
          <p className="text-red-500">{error}</p>
          <Button onClick={loadSkills} className="mt-4">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-2xl mx-auto p-6">
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Select your skills</h2>
          <p className="text-muted-foreground mt-2">
            Choose the skills you have and set your proficiency level
          </p>
        </div>

        <div className="space-y-6">
          {Object.entries(groupedSkills).map(([category, categorySkills]) => (
            <div key={category} className="space-y-3">
              <h3 className="text-lg font-semibold capitalize">{category}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {categorySkills.map((skill) => {
                  const isSelected = selectedSkills[skill.id]
                  return (
                    <div
                      key={skill.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => toggleSkill(skill.id)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{skill.name}</span>
                        <input
                          type="checkbox"
                          checked={!!isSelected}
                          onChange={() => toggleSkill(skill.id)}
                          className="ml-2"
                        />
                      </div>
                      
                      {isSelected && (
                        <div className="mt-3">
                          <label className="text-sm text-muted-foreground mb-1 block">
                            Proficiency Level:
                          </label>
                          <select
                            value={selectedSkills[skill.id]}
                            onChange={(e) => updateProficiency(skill.id, e.target.value)}
                            className="w-full p-2 border rounded text-sm"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {PROFICIENCY_LEVELS.map((level) => (
                              <option key={level.value} value={level.value}>
                                {level.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
          <Button onClick={handleNext}>
            Continue
          </Button>
        </div>
      </div>
    </Card>
  )
}
