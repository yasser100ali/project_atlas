import { motion } from "framer-motion";
import Link from "next/link";

import { MessageIcon } from "./icons";
import { LogoPython } from "@/app/icons";

export const Overview = () => {
  return (
    <motion.div
      key="overview"
      className="max-w-3xl mx-auto md:mt-20"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ delay: 0.5 }}
    >
      <div className="rounded-xl p-6 flex flex-col gap-8 leading-relaxed text-center max-w-xl">
        <p className="flex flex-row justify-center gap-4 items-center">
          <LogoPython size={32} />
          <span>+</span>
          <MessageIcon size={32} />
        </p>
        <p className="text-xl font-semibold">Apex AI</p>
        <p>
          Personal agents for peak productivity. Apex AI builds task-focused
          agents for job discovery, resume crafting, research, and outreach—so
          you move faster with less friction.
        </p>
        <p>
          Powered by Python (FastAPI) and modern React with streaming for a
          smooth, low‑latency chat experience.
        </p>
      </div>
    </motion.div>
  );
};