import type { Metadata } from "next";
import { Suspense } from "react";
import QuizApp from "@/components/quiz/QuizApp";
import { estruturaCliente } from "@/lib/quiz/estrutura";

export const metadata: Metadata = {
  title: "Que cientista é você? — Ciência Nordeste",
  description: "Um quiz rápido: descubra o seu perfil de cientista e quem no Nordeste pesquisa como você.",
};

export const dynamic = "force-dynamic";   // lê CONTATO_PRIVACIDADE em tempo de execução

// A estrutura vai enxuta para o navegador (sem os sinais do match, que ficam no servidor).
export default function Quiz() {
  return <Suspense><QuizApp estrutura={estruturaCliente()} contato={process.env.CONTATO_PRIVACIDADE || null} /></Suspense>;
}
