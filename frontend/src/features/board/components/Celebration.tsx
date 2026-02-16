import confetti from "canvas-confetti";
import { useCallback, useEffect, useState } from "react";

interface CelebrationProps {
	show: boolean;
}

export function Celebration({ show }: CelebrationProps) {
	const [visible, setVisible] = useState(false);

	const fireCelebration = useCallback(() => {
		// Fire confetti from both sides
		const duration = 3000;
		const end = Date.now() + duration;

		const frame = () => {
			confetti({
				particleCount: 3,
				angle: 60,
				spread: 55,
				origin: { x: 0, y: 0.6 },
				colors: ["#f59e0b", "#10b981", "#6366f1", "#ec4899"],
			});
			confetti({
				particleCount: 3,
				angle: 120,
				spread: 55,
				origin: { x: 1, y: 0.6 },
				colors: ["#f59e0b", "#10b981", "#6366f1", "#ec4899"],
			});

			if (Date.now() < end) {
				requestAnimationFrame(frame);
			}
		};

		frame();
	}, []);

	useEffect(() => {
		if (show) {
			setVisible(true);
			fireCelebration();
			const timer = setTimeout(() => setVisible(false), 5000);
			return () => clearTimeout(timer);
		}
	}, [show, fireCelebration]);

	const dismiss = () => setVisible(false);

	if (!visible) return null;

	return (
		<button
			type="button"
			className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm border-none cursor-default"
			onClick={dismiss}
			onKeyDown={(e) => {
				if (e.key === "Escape" || e.key === "Enter") dismiss();
			}}
		>
			<div className="rounded-2xl bg-white/90 dark:bg-gray-900/90 px-12 py-8 shadow-2xl text-center animate-in zoom-in-95 fade-in duration-300">
				<p className="text-5xl mb-3">🏆</p>
				<h2 className="text-3xl font-bold text-amber-600 dark:text-amber-400 mb-2">
					Goal Complete!
				</h2>
				<p className="text-muted-foreground">Congratulations on achieving your goal!</p>
			</div>
		</button>
	);
}
