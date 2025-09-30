"use client";

import { Button } from "@/components/ui/button";
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { Menu, MoveRight, X } from "lucide-react";
import { useState, useEffect } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { redirect } from "next/navigation";
interface NavigationItem {
    title: string;
    description: string;
    href: string;
    items?: NavigationItem[];
}

function Header() {
    const navigationItems: NavigationItem[] = [
        {
            title: "Home",
            href: "/",
            description: "",
        },
        {
            title: "Features",
            description: "Our features are designed to help you find the perfect job.",
            href: "#Features",
        },
        {
            title: "How it works",
            description: "How our agent works to find the perfect job for you.",
            href: "#How it works",
        },
    ];

    const [isOpen, setOpen] = useState(false);
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const logout = async () => {
        const supabase = createClient();
        await supabase.auth.signOut();
        setUser(null);
        redirect('/')
    }
    useEffect(() => {
        const supabase = createClient();
        
        const getUser = async () => {
            try {
                const { data, error } = await supabase.auth.getUser();
                if (!error && data?.user) {
                    setUser(data.user);
                }
            } catch (error) {
                console.error('Error fetching user:', error);
            } finally {
                setLoading(false);
            }
        };

        getUser();
    }, []);
    return (
        <header className="w-full z-40 fixed top-0 left-0 bg-secondary rounded-b-lg">
            <div className="container relative mx-auto min-h-20 flex items-center justify-between">
                {/* Desktop Navigation - Hidden on mobile */}
                <div className="hidden lg:flex justify-start items-center gap-4 flex-row">
                    <NavigationMenu className="flex justify-start items-start">
                        <NavigationMenuList className="flex justify-start gap-4 flex-row">
                            {navigationItems.map((item) => (
                                <NavigationMenuItem key={item.title}>
                                    {item.href ? (
                                        <>
                                            <NavigationMenuLink>
                                                <Button variant="ghost">{item.title}</Button>
                                            </NavigationMenuLink>
                                        </>
                                    ) : (
                                        <>
                                            <NavigationMenuTrigger className="font-medium text-sm">
                                                {item.title}
                                            </NavigationMenuTrigger>
                                            <NavigationMenuContent className="!w-[450px] p-4">
                                                <div className="flex flex-col lg:grid grid-cols-2 gap-4">
                                                    <div className="flex flex-col h-full justify-between">
                                                        <div className="flex flex-col">
                                                            <p className="text-base">{item.title}</p>
                                                            <p className="text-muted-foreground text-sm">
                                                                {item.description}
                                                            </p>
                                                        </div>
                                                        <Button size="sm" className="mt-10">
                                                            Book a call today
                                                        </Button>
                                                    </div>
                                                    <div className="flex flex-col text-sm h-full justify-end">
                                                        {item.items?.map((subItem) => (
                                                            <NavigationMenuLink
                                                                href={subItem.href}
                                                                key={subItem.title}
                                                                className="flex flex-row justify-between items-center hover:bg-muted py-2 px-4 rounded"
                                                            >
                                                                <span>{subItem.title}</span>
                                                                <MoveRight className="w-4 h-4 text-muted-foreground" />
                                                            </NavigationMenuLink>
                                                        ))}
                                                    </div>
                                                </div>
                                            </NavigationMenuContent>
                                        </>
                                    )}
                                </NavigationMenuItem>
                            ))}
                        </NavigationMenuList>
                    </NavigationMenu>
                </div>

                {/* Title - Centered on all screen sizes */}
                <div className="flex justify-center flex-1">
                    <p className="font-semibold text-center">E2E Job Search Agent</p>
                </div>

                {/* Desktop Auth Buttons - Hidden on mobile */}
                <div className="hidden lg:flex justify-end gap-4">
                    {user ? (
                        <Button variant="outline" onClick={logout}>Sign out</Button>
                    ) : (
                        <>
                            <Button variant="outline"><Link href="/auth/login">Sign in</Link></Button>
                            <Button><Link href="/auth/sign-up">Get started</Link></Button>
                        </>
                    )}
                </div>

                {/* Mobile Hamburger Menu - Only visible on mobile */}
                <div className="flex lg:hidden">
                    <Button variant="ghost" onClick={() => setOpen(!isOpen)}>
                        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                    </Button>
                    {isOpen && (
                        <>
                            {/* Backdrop overlay with blur */}
                            <div 
                                className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[-1]"
                                onClick={() => setOpen(false)}
                            />
                            
                            {/* Mobile menu */}
                            <div className="absolute mt-4 top-20 left-0 right-0 border-t flex flex-col w-full shadow-lg py-4 px-4 gap-8 bg-secondary rounded-lg">
                                {navigationItems.map((item) => (
                                    <div key={item.title}>
                                        <div className="flex flex-col gap-2">
                                            {item.href ? (
                                                <Link
                                                    href={item.href}
                                                    className="flex justify-between items-center"
                                                    onClick={() => setOpen(false)}
                                                >
                                                    <span className="text-lg">{item.title}</span>
                                                    <MoveRight className="w-4 h-4 stroke-1 text-muted-foreground" />
                                                </Link>
                                            ) : (
                                                <p className="text-lg">{item.title}</p>
                                            )}
                                            {item.items &&
                                                item.items.map((subItem) => (
                                                    <Link
                                                        key={subItem.title}
                                                        href={subItem.href}
                                                        className="flex justify-between items-center"
                                                        onClick={() => setOpen(false)}
                                                    >
                                                        <span className="text-muted-foreground">
                                                            {subItem.title}
                                                        </span>
                                                        <MoveRight className="w-4 h-4 stroke-1" />
                                                    </Link>
                                                ))}
                                        </div>
                                    </div>
                                ))}
                                
                                {/* Mobile auth buttons */}
                                <div className="flex flex-col gap-4 pt-4 border-t">
                                    {user ? (
                                        <Button variant="outline" className="w-full" onClick={logout}>Sign out</Button>
                                    ) : (
                                        <>
                                            <Button variant="outline" className="w-full"><Link href="/auth/login">Sign in</Link></Button>
                                            <Button className="w-full"><Link href="/auth/sign-up">Get started</Link></Button>
                                        </>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
}

export { Header };