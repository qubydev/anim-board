import React from 'react'
import { Dock, DockIcon } from "@/components/ui/dock"
import { FaVideo } from 'react-icons/fa'
import { MdSpaceDashboard } from "react-icons/md";
import { Link } from 'react-router-dom'
import { useLocation } from 'react-router-dom'

export default function DockMenu() {
    const location = useLocation()

    const isActive = (path) => {
        return location.pathname === path
    }

    return (
        <div className="fixed bottom-3 right-3">
            <Dock direction="middle" className="shadow-lg">
                <DockIcon
                    className={isActive("/") ? "text-primary" : "text-muted-foreground"}
                >
                    <Link to="/">
                        <MdSpaceDashboard className="size-5" />
                    </Link>
                </DockIcon>
                <DockIcon
                    className={isActive("/render") ? "text-primary" : "text-muted-foreground"}
                >
                    <Link to="/render">
                        <FaVideo className="size-5" />
                    </Link>
                </DockIcon>
            </Dock>
        </div>
    )
}
