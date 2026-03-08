import { useNavigate } from "@tanstack/react-router";
import { LogOut, Settings, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth, useLogout } from "@/features/auth/hooks/use-auth";

export function UserDropdown() {
	const { user } = useAuth();
	const logout = useLogout();
	const navigate = useNavigate();

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button variant="ghost" size="sm" className="gap-2">
					<User className="h-4 w-4" />
					<span className="max-w-[200px] truncate text-sm">{user?.email}</span>
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end">
				<DropdownMenuItem onClick={() => navigate({ to: "/settings" })}>
					<Settings className="mr-2 h-4 w-4" />
					Settings
				</DropdownMenuItem>
				<DropdownMenuSeparator />
				<DropdownMenuItem onClick={() => logout.mutate()} disabled={logout.isPending}>
					<LogOut className="mr-2 h-4 w-4" />
					{logout.isPending ? "Logging out..." : "Log out"}
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
