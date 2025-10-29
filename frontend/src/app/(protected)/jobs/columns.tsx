"use client"

import { ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown, MoreHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"

import { JobListing } from "./types"

export const columns: ColumnDef<JobListing>[] = [
  {
    accessorKey: "title",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Job Title
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      )
    },
    cell: ({ row }) => {
      return (
        <div className="font-medium max-w-[300px] truncate">
          {row.getValue("title")}
        </div>
      )
    },
  },
  {
    accessorKey: "company",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Company
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      )
    },
    cell: ({ row }) => {
      return (
        <div className="font-medium">
          {row.getValue("company")}
        </div>
      )
    },
  },
  {
    accessorKey: "snippit",
    header: "Description",
    cell: ({ row }) => {
      return (
        <div className="max-w-[400px] text-sm text-muted-foreground whitespace-normal break-words">
          {row.getValue("snippit")}
        </div>
      )
    },
    
  },
  {
    accessorKey: "rating",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Match Rating
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      )
    },
    cell: ({ row }) => {
      const rating = parseFloat(row.getValue("rating"))
      const percentage = Math.round(rating * 100)
      
      return (
        <div className="flex items-center gap-2">
          <Badge 
            variant={percentage >= 80 ? "default" : percentage >= 60 ? "secondary" : "outline"}
            className="font-medium ml-2"
          >
            {percentage}%
          </Badge>
        </div>
      )
    },
  },
  {
    accessorKey: "link",
    header: "Apply",
    cell: ({ row }) => {
      const link = row.getValue("link") as string
      
      return (
        <Button
          variant="default"
          size="sm"
          onClick={() => window.open(link, '_blank', 'noopener,noreferrer')}
          className="font-medium"
        >
          Apply
        </Button>
      )
    },
  },
 
]
