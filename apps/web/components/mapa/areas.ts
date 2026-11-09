// Ordem fixa das áreas (define a cor --area-N de cada uma em mapa.css) e nomes em português.
export const AREAS_ORDEM = [
  "Medicine",
  "Agricultural and Biological Sciences",
  "Health Professions",
  "Dentistry",
  "Biochemistry, Genetics and Molecular Biology",
  "Nursing",
  "Immunology and Microbiology",
  "Neuroscience",
  "Pharmacology, Toxicology and Pharmaceutics",
  "Veterinary",
];
const NOMES: Record<string, string> = {
  Medicine: "Medicina",
  "Agricultural and Biological Sciences": "Ciências agrárias e biológicas",
  "Health Professions": "Profissões da saúde",
  Dentistry: "Odontologia",
  "Biochemistry, Genetics and Molecular Biology": "Bioquímica, genética e biol. molecular",
  Nursing: "Enfermagem",
  "Immunology and Microbiology": "Imunologia e microbiologia",
  Neuroscience: "Neurociência",
  "Pharmacology, Toxicology and Pharmaceutics": "Farmacologia e toxicologia",
  Veterinary: "Veterinária",
};
export const rotuloArea = (f: string) => NOMES[f] ?? f;
