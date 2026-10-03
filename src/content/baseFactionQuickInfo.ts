export interface BaseFactionQuickInfo {
  summary: string;
  style: readonly string[];
  strengths: readonly string[];
  attention: readonly string[];
}

export const baseFactionQuickInfo = {
  "the-arborec": {
    summary: "Expande sua presença por meio das tropas Letani, que também funcionam como unidades de produção.",
    style: ["Produção móvel", "Infantaria", "Expansão"],
    strengths: ["Produz unidades nos planetas ocupados por tropas Letani.", "Mitosis adiciona uma tropa Letani a cada rodada.", "Pode aumentar a produção à medida que ocupa novos planetas."],
    attention: ["A capacidade de produção acompanha a quantidade de tropas Letani disponíveis.", "Não pode pesquisar a tecnologia Infantry II convencional."],
  },
  "the-barony-of-letnev": {
    summary: "Opera frotas maiores e possui ferramentas para sustentar combates espaciais prolongados.",
    style: ["Frotas grandes", "Combate espacial", "Sustain Damage"],
    strengths: ["Armada permite 2 navios não fighter além do limite de frota.", "Munitions Reserves permite rerrolar dados em uma rodada de combate espacial.", "Começa com um dreadnought e duas tecnologias."],
    attention: ["Munitions Reserves consome 2 trade goods por uso.", "Seu foco em navios pesados exige recursos e capacidade de frota."],
  },
  "the-clan-of-saar": {
    summary: "Move sua infraestrutura pelo mapa e produz unidades com suas Floating Factories.",
    style: ["Mobilidade", "Produção móvel", "Expansão"],
    strengths: ["Floating Factories podem se mover e produzir fora de sistemas natais.", "Scavenge concede 1 trade good após obter controle de um planeta.", "Pode manter produção sem depender de space docks planetários."],
    attention: ["Floating Factories bloqueadas por navios adversários podem ser destruídas.", "Perder a infraestrutura móvel reduz diretamente suas opções de produção."],
  },
  "the-embers-of-muaat": {
    summary: "Começa com uma War Sun e desenvolve sua presença ao redor dessa unidade singular.",
    style: ["War Sun", "Projeção de força", "Produção"],
    strengths: ["Inicia a partida com uma War Sun disponível.", "Star Forge converte um token de estratégia em fighters ou destroyers.", "A tecnologia Gashlai Prototype reduz o custo de futuras War Suns."],
    attention: ["A frota inicial concentra grande parte de seu valor em uma única War Sun.", "War Suns continuam exigindo muitos recursos para serem produzidas."],
  },
  "the-emirates-of-hacan": {
    summary: "Amplia as possibilidades de negociação e transforma commodities em uma economia flexível.",
    style: ["Comércio", "Negociação", "Economia"],
    strengths: ["Pode realizar transações com jogadores que não são vizinhos.", "Pode negociar action cards durante a Action Phase.", "Masters of Trade elimina o custo de command token da ação secundária de Trade."],
    attention: ["Grande parte de sua vantagem depende de oportunidades de negociação.", "Suas habilidades de facção não fornecem bônus direto de combate."],
  },
  "the-federation-of-sol": {
    summary: "Combina transporte eficiente, infantaria resistente e reforços regulares para ocupar planetas.",
    style: ["Infantaria", "Capacidade", "Command tokens"],
    strengths: ["Recebe 1 command token adicional em cada Status Phase.", "Orbital Drop coloca 2 infantry em um planeta controlado.", "Advanced Carriers transportam mais unidades que carriers comuns."],
    attention: ["Orbital Drop consome um token da strategy pool.", "Sua presença planetária depende de manter transporte e reforços disponíveis."],
  },
  "the-ghosts-of-creuss": {
    summary: "Usa wormholes para criar rotas incomuns e alcançar sistemas distantes com rapidez.",
    style: ["Wormholes", "Mobilidade", "Posicionamento"],
    strengths: ["Seus navios recebem movimento adicional ao sair do sistema natal.", "Trata sistemas com wormholes alpha e beta como adjacentes entre si.", "A Creuss Gate conecta o sistema natal ao tabuleiro."],
    attention: ["O sistema natal começa separado do restante do mapa.", "O melhor uso das habilidades depende da posição dos wormholes."],
  },
  "the-l1z1x-mindnet": {
    summary: "Avança com dreadnoughts e bombardeio, incorporando estruturas dos planetas conquistados.",
    style: ["Dreadnoughts", "Bombardment", "Conquista"],
    strengths: ["Assimilate substitui PDS e space docks inimigos após conquistar um planeta.", "Harrow permite novo bombardeio após cada rodada de ground combat.", "Super-Dreadnoughts combinam movimento e capacidade superiores."],
    attention: ["Seu plano de ocupação depende de vencer combates terrestres.", "Frotas centradas em dreadnoughts exigem investimento relevante."],
  },
  "the-mentak-coalition": {
    summary: "Pressiona economias vizinhas e abre combates espaciais com fogo antecipado de navios leves.",
    style: ["Cruisers", "Trade goods", "Emboscada"],
    strengths: ["Ambush permite disparos antecipados de até 2 cruisers ou destroyers.", "Pillage pode capturar 1 trade good de vizinhos que acumulem pelo menos 3.", "Mirror Computing aumenta o valor gasto de cada trade good."],
    attention: ["Pillage exige proximidade e trade goods disponíveis nos vizinhos.", "Ambush depende de cruisers ou destroyers presentes no combate."],
  },
  "the-naalu-collective": {
    summary: "Age primeiro pela iniciativa 0 e usa fighters eficientes para proteger e projetar sua frota.",
    style: ["Iniciativa", "Fighters", "Reposicionamento"],
    strengths: ["O token 0 faz a facção agir antes das demais na ordem de iniciativa.", "Foresight permite retirar unidades quando um sistema é ativado por outro jogador.", "Hybrid Crystal Fighter II tem movimento 2 e não ocupa capacidade."],
    attention: ["Foresight exige um token da strategy pool.", "Fighters ainda dependem de capacidade para acompanhar a frota."],
  },
  "the-nekro-virus": {
    summary: "Obtém tecnologias ao destruir unidades inimigas e ganha command tokens quando outros pesquisam.",
    style: ["Cópia de tecnologia", "Combate", "Command tokens"],
    strengths: ["Pode copiar tecnologia de facção adversária após destruir uma unidade em combate.", "Recebe command tokens quando outros jogadores pesquisam tecnologia.", "Valefar Assimilators permitem manter tecnologias copiadas de facção."],
    attention: ["Não pode pesquisar tecnologia pelo processo normal.", "Não pode votar em agendas e prevê resultados em vez disso.", "A aquisição de tecnologia exige contato de combate com unidades adequadas."],
  },
  "sardakk-norr": {
    summary: "Aplica um bônus direto a todas as suas rolagens de combate e dispõe de dreadnoughts ofensivos.",
    style: ["Combate", "Dreadnoughts", "Pressão militar"],
    strengths: ["Unrelenting concede +1 ao resultado de cada dado de combate.", "Exotrireme II pode se destruir após Sustain Damage para destruir 2 navios adversários.", "O bônus de combate vale para todas as classes de unidade."],
    attention: ["Começa sem qualquer tecnologia.", "Precisa recuperar a defasagem tecnológica durante a partida."],
  },
  "the-universities-of-jol-nar": {
    summary: "Pesquisa com mais frequência e ignora parte dos pré-requisitos, em troca de menor eficiência em combate.",
    style: ["Tecnologia", "Flexibilidade", "Pesquisa"],
    strengths: ["Pode resolver a ação primária de Technology ao pagar pela ação secundária.", "Pode pesquisar sem cumprir um pré-requisito pela habilidade Analytical.", "Começa com quatro tecnologias."],
    attention: ["Fragile aplica -1 a todas as rolagens de combate.", "A pesquisa adicional da ação primária exige o pagamento indicado pela habilidade."],
  },
  "the-winnu": {
    summary: "Concentra suas habilidades em alcançar Mecatol Rex e estabelecer infraestrutura no sistema central.",
    style: ["Mecatol Rex", "Objetivos", "Infraestrutura"],
    strengths: ["Reclamation instala gratuitamente um PDS e um space dock ao conquistar Mecatol Rex.", "Blood Ties evita o custo de influência para remover o token custodians.", "Pode escolher qualquer tecnologia sem pré-requisitos como tecnologia inicial."],
    attention: ["Várias habilidades dependem especificamente do controle de Mecatol Rex.", "A frota inicial tem transporte limitado."],
  },
  "the-xxcha-kingdom": {
    summary: "Controla interações políticas e territoriais com respostas defensivas e influência sobre agendas.",
    style: ["Diplomacia", "Agenda", "Defesa"],
    strengths: ["Peace Accords pode obter um planeta não controlado adjacente após Diplomacy.", "Quash descarta uma agenda revelada e força uma nova revelação.", "Instinct Training pode cancelar um action card adversário."],
    attention: ["Quash e Instinct Training consomem tokens da strategy pool.", "Peace Accords depende do uso de Diplomacy e de um planeta elegível."],
  },
  "the-yin-brotherhood": {
    summary: "Converte infantaria inimiga, troca navios leves por acertos e ameaça combates com sua flagship explosiva.",
    style: ["Infantaria", "Sacrifício", "Ground combat"],
    strengths: ["Indoctrination substitui uma infantry adversária por uma infantry Yin.", "Devotion pode destruir um cruiser ou destroyer próprio para produzir um acerto.", "A flagship Van Hauge destrói todas as unidades no sistema quando é destruída."],
    attention: ["Indoctrination exige influência disponível.", "Devotion e a flagship dependem do sacrifício de unidades próprias."],
  },
  "the-yssaril-tribes": {
    summary: "Acumula e manipula action cards para obter informação, flexibilidade e controle do ritmo das ações.",
    style: ["Action cards", "Informação", "Ritmo"],
    strengths: ["Scheming compra um action card adicional sempre que recebe action cards.", "Stall Tactics troca um action card por uma ação sem movimento de unidades.", "Mageon Implants permite examinar e tomar um action card de outro jogador."],
    attention: ["Scheming também exige descartar um action card após a compra.", "Suas principais opções dependem da qualidade e do tamanho da mão de action cards."],
  },
} as const satisfies Record<string, BaseFactionQuickInfo>;

export type BaseFactionSlug = keyof typeof baseFactionQuickInfo;

export function getBaseFactionQuickInfo(slug: string): BaseFactionQuickInfo | null {
  return Object.prototype.hasOwnProperty.call(baseFactionQuickInfo, slug)
    ? baseFactionQuickInfo[slug as BaseFactionSlug]
    : null;
}
