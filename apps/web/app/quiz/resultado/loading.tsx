import Processando from "@/components/quiz/Processando";

// Enquanto o servidor calcula o match e monta a página de resultado.
export default function Carregando() {
  return <div className="quiz"><Processando /></div>;
}
