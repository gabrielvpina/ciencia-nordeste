// Nomes dos fields do OpenAlex em português (UI) e as UFs do recorte.
export const AREAS: Record<string, string> = {
  Medicine: "Medicina",
  "Agricultural and Biological Sciences": "Ciências agrárias e biológicas",
  "Health Professions": "Profissões da saúde",
  Dentistry: "Odontologia",
  "Biochemistry, Genetics and Molecular Biology": "Bioquímica, genética e biologia molecular",
  Nursing: "Enfermagem",
  "Immunology and Microbiology": "Imunologia e microbiologia",
  Neuroscience: "Neurociência",
  "Pharmacology, Toxicology and Pharmaceutics": "Farmacologia e toxicologia",
  Veterinary: "Veterinária",
};
export const area = (f: string | null | undefined) => (f ? AREAS[f] ?? f : "");

export const UFS: [string, string][] = [
  ["MA", "Maranhão"], ["PI", "Piauí"], ["CE", "Ceará"], ["RN", "Rio Grande do Norte"], ["PB", "Paraíba"],
  ["PE", "Pernambuco"], ["AL", "Alagoas"], ["SE", "Sergipe"], ["BA", "Bahia"],
];
export const ufValida = (uf?: string) => (uf && UFS.some(([s]) => s === uf) ? uf : undefined);

export const fmt = (n: string | number | null | undefined) => (n == null ? "—" : Number(n).toLocaleString("pt-BR"));

export const TIPOS_INSTITUICAO: Record<string, string> = {
  universidade: "Universidade", centro_universitario: "Centro universitário", faculdade: "Faculdade",
  instituto_federal: "Instituto federal", cefet: "CEFET", ensino: "Ensino", hospital_saude: "Hospital / saúde",
  instituto_pesquisa: "Instituto de pesquisa", governo: "Governo", empresa: "Empresa",
  organizacao_sem_fins_lucrativos: "Organização sem fins lucrativos", financiador: "Financiador", arquivo: "Arquivo", outro: "Outro",
};
