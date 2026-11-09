// Recursos ligados/desligados por ambiente. Login com ORCID só em produção (D-024): fora dela, nenhuma tela de login aparece.
export const RECURSOS = {
  login: process.env.LOGIN_HABILITADO === "true",
};
