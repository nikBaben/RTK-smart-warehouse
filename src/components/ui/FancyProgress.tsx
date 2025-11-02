
import { motion } from "framer-motion";
export function FancyProgress({ value }: { value: number }) {
	return (
		<div className="relative w-[80%] h-[20px] rounded-[5px] bg-[#E5E7EB] overflow-hidden shadow-inner">
			<motion.div
				className="absolute top-0 left-0 h-full rounded-[5px] bg-[#7700FF]"
				initial={{ width: 0 }}
				animate={{ width: `${value}%` }}
				transition={{ duration: 0.3, ease: "easeOut" }}
				style={{
					boxShadow: "0 0 12px rgba(119, 0, 255, 0.4)",
				}}
			/>
			<motion.div
				className="absolute top-0 left-0 h-full w-1/4 bg-white/25 blur-sm rounded-[5px]"
				animate={{
					x: ["-100%", "400%"],
				}}
				transition={{
					repeat: Infinity,
					duration: 1.8,
					ease: "linear",
				}}
			/>
		</div>
	);
}