'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText, Download, ExternalLink, User, Calendar } from 'lucide-react'
import Link from 'next/link'

interface ResumeCardProps {
  resume: {
    id: string
    file_name: string
    file_url: string
    is_master: boolean
    created_at: string
    updated_at: string
    parsed_content?: any
    profiles: {
      id: string
      full_name: string
      email: string
      linkedin_url?: string
    }
  }
}

export function ResumeCard({ resume }: ResumeCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const handleDownload = () => {
    window.open(resume.file_url, '_blank')
  }

  return (
    <Card className="group hover:shadow-lg transition-all duration-200 border-border/60">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-lg font-semibold line-clamp-1">
                {resume.file_name}
              </CardTitle>
              <CardDescription className="flex items-center gap-1 mt-1">
                <User className="h-3 w-3" />
                {resume.profiles.full_name}
              </CardDescription>
            </div>
          </div>
          {resume.is_master && (
            <Badge variant="default" className="bg-primary/10 text-primary border-primary/20">
              Master
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* Resume metadata */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>Created {formatDate(resume.created_at)}</span>
            </div>
            {resume.updated_at !== resume.created_at && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>Updated {formatDate(resume.updated_at)}</span>
              </div>
            )}
          </div>

          {/* Parsed content preview */}
          {resume.parsed_content && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-foreground">Content Preview:</h4>
              <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded-md">
                {typeof resume.parsed_content === 'string' 
                  ? resume.parsed_content.slice(0, 150) + '...'
                  : 'Structured resume data available'
                }
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDownload}
              className="flex-1"
            >
              <Download className="h-3 w-3 mr-1" />
              Download
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              asChild
              className="flex-1"
            >
              <Link href={resume.file_url} target="_blank">
                <ExternalLink className="h-3 w-3 mr-1" />
                View
              </Link>
            </Button>
          </div>

          {/* LinkedIn link if available */}
          {resume.profiles.linkedin_url && (
            <div className="pt-2 border-t border-border/60">
              <Button 
                variant="ghost" 
                size="sm" 
                asChild
                className="w-full text-xs"
              >
                <Link href={resume.profiles.linkedin_url} target="_blank">
                  <ExternalLink className="h-3 w-3 mr-1" />
                  View LinkedIn Profile
                </Link>
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
