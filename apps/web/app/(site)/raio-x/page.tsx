import type { Metadata } from "next";
import { ReadingCard } from "@/components/site/reading-card";
import { Section } from "@/components/site/section";
import { Card } from "@/components/ui/card";
import { Disclaimer } from "@/components/ui/disclaimer";
import { EmailCapture } from "@/components/ui/email-capture";
import { Gold } from "@/components/ui/gold";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { READINGS, SAMPLE_PORTFOLIO } from "@/content/site";

export const metadata: Metadata = {
  title: "O raio-x de carteira",
  description:
    "As cinco leituras de risco — concentração, correlação, exposição, drawdown e liquidez — aplicadas a uma carteira ilustrativa de R$ 120 mil com 11 ativos.",
  alternates: { canonical: "/raio-x" },
};

const byId = (slug: string) => READINGS.find((r) => r.slug === slug)!;

// Números do vídeo 02 (ferramentas/raio-x-carteira.py, referência 18/09/2026).
export default function RaioXPage() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          O que é o <Gold>raio-x</Gold> de carteira
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">
          Olhar o que você já tem e responder cinco perguntas. Não diz o que comprar ou vender: é leitura de risco, em
          português. Abaixo, as cinco aplicadas a uma carteira ilustrativa.
        </p>
      </Section>

      <Section
        heading={
          <>
            A <Gold>carteira</Gold> ilustrativa
          </>
        }
        intro={`Fictícia, mas realista: alguém que começou em cripto em 2021, se assustou na queda e "diversificou" comprando ação e fundo imobiliário. ${SAMPLE_PORTFOLIO.total} em 11 ativos, preços de ${SAMPLE_PORTFOLIO.referenceDate}. Não é sugestão de alocação.`}
      >
        <Table caption="Composição da carteira ilustrativa por ativo, classe e peso">
          <Thead>
            <Tr>
              <Th>Ativo</Th>
              <Th>Classe</Th>
              <Th className="text-right">Peso</Th>
            </Tr>
          </Thead>
          <tbody>
            {SAMPLE_PORTFOLIO.positions.map((p) => (
              <Tr key={p.asset}>
                <Td>{p.asset}</Td>
                <Td className="text-ice-70">{p.klass}</Td>
                <Td numeric>{p.weight}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
        <p className="mt-3 text-xs text-ice-70">
          Onze linhas, quatro classes. Parece equilibrado. Agora as cinco leituras.
        </p>
      </Section>

      {/* 1. Concentração */}
      <Section id="concentracao" heading={<>1. Você está <Gold>concentrado</Gold>?</>}>
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ReadingCard reading={byId("concentracao")} />
          <div className="space-y-4 text-ice-70">
            <p>
              Concentração é quanto da carteira depende de poucos ativos. Maior posição: Bitcoin, <strong className="text-ice">38%</strong>.
              As três maiores (Bitcoin, Tesouro Selic e Ethereum) somam 58%; as cinco maiores, 73%. Por classe, cripto é 50%.
              Somando o que é denominado em dólar (cripto mais a stablecoin), 55%.
            </p>
            <p>
              O{" "}
              <Tooltip content="Índice de Herfindahl-Hirschman: soma dos pesos ao quadrado. Quanto maior, mais concentrada a carteira. 1 ÷ HHI dá o número de ativos equivalentes.">
                HHI
              </Tooltip>{" "}
              dessa carteira é 0,189 — o equivalente a <strong className="text-ice">5,3 ativos</strong>. São onze linhas, mas,
              em termos de risco, é como se fossem cinco. Diversificação é sobre peso, não sobre quantidade.
            </p>
            <p>Isso é bom ou ruim? Depende do dono. O problema não é o número — é não saber o número.</p>
          </div>
        </div>
      </Section>

      {/* 2. Correlação */}
      <Section id="correlacao" heading={<>2. Seus ativos andam <Gold>juntos</Gold>?</>}>
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ReadingCard reading={byId("correlacao")} />
          <div className="space-y-4 text-ice-70">
            <p>
              <Tooltip content="Medida de quanto dois ativos sobem e caem ao mesmo tempo: 1 = iguais, 0 = sem relação, negativo = ao contrário. Aqui, calculada sobre os últimos 12 meses.">
                Correlação
              </Tooltip>{" "}
              é o quanto dois ativos andam juntos. Bitcoin com Ethereum: <strong className="text-ice">0,91</strong>. Bitcoin com
              Solana: 0,87. Ethereum com Solana: 0,90. São três nomes para a mesma aposta — e esse bloco é metade da carteira.
            </p>
            <p>
              O dado corrige a intuição: Petrobras e Vale, as duas &ldquo;exportadoras&rdquo;, tiveram correlação de −0,05 no
              último ano. Zero. As quatro ações entre si ficam entre 0,06 e 0,34; os dois FIIs, 0,38; cripto com ação, 0,07.
            </p>
            <p>O resto está razoavelmente espalhado. O problema não é a diversificação do resto; é o tamanho do bloco.</p>
          </div>
        </div>
      </Section>

      {/* 3. Exposição */}
      <Section id="exposicao" heading={<>3. A que você está <Gold>exposto</Gold>?</>}>
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ReadingCard reading={byId("exposicao")} />
          <div className="space-y-4 text-ice-70">
            <p>
              Um{" "}
              <Tooltip content="Uma força que mexe em vários ativos ao mesmo tempo: dólar, juros, petróleo, o humor do mercado cripto.">
                fator
              </Tooltip>{" "}
              é uma força que mexe em vários ativos de uma vez. Por fator: cripto 50%, juros brasileiros 22%, bolsa brasileira 11%,
              dólar direto 9%, commodities 9%.
            </p>
            <p>
              Medindo o valor total da carteira, dia a dia, por três anos: correlação de{" "}
              <strong className="text-ice">0,96</strong> com o Bitcoin e{" "}
              <Tooltip content="Sensibilidade: quanto a carteira se mexe para cada 1% de movimento da referência.">beta</Tooltip>{" "}
              de 0,54 — para cada 1% do Bitcoin, a carteira se mexe 0,54%. Com o dólar, correlação de só 0,18 (apesar de 55%
              denominados em dólar: o Bitcoin abafa o câmbio). Com o Ibovespa, 0,21.
            </p>
            <p>É uma carteira de Bitcoin com enfeites. Impossível ver isso olhando para a lista de onze ativos.</p>
          </div>
        </div>
      </Section>

      {/* 4. Drawdown */}
      <Section id="drawdown" heading={<>4. Quanto ela já <Gold>caiu</Gold>?</>}>
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ReadingCard reading={byId("drawdown")} />
          <div className="space-y-4 text-ice-70">
            <p>
              <Tooltip content="A maior queda do topo ao fundo em um período. Responde a: qual o pior que já aconteceu com esta composição?">
                Drawdown
              </Tooltip>{" "}
              é o quanto a carteira caiu do topo ao fundo. Com a composição de hoje, voltando três anos: topo em 06/10/2025
              (R$ 152 mil), fundo em 05/06/2026 (R$ 99,8 mil). Queda de <strong className="text-ice">34,4%</strong> em oito meses
              — e ainda 21% abaixo do topo na data de referência.
            </p>
            <p>
              Pior mês: fevereiro de 2025, −15,2%. Melhor: novembro de 2024, +25,2%. Volatilidade anual de 27,9% (o Ibovespa
              fica perto de 17%; o Bitcoin, de 45%). Três anos antes, a mesma composição valia R$ 69 mil: +73% no período.
            </p>
            <p>
              A questão não é se ganhou — é se o dono sabia que, no caminho, veria R$ 52 mil sumirem por mais de um ano. Quem
              vende no fundo transforma queda temporária em perda permanente.
            </p>
          </div>
        </div>
      </Section>

      {/* 5. Liquidez */}
      <Section id="liquidez" heading={<>5. Em quanto tempo você <Gold>sai</Gold>?</>}>
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ReadingCard reading={byId("liquidez")} />
          <div className="space-y-4 text-ice-70">
            <p>
              <Tooltip content="Em quanto tempo você transforma o ativo em dinheiro sem derrubar o preço. Medida aqui pelo volume médio negociado em 30 dias.">
                Liquidez
              </Tooltip>{" "}
              é em quanto tempo você transforma o ativo em dinheiro sem derrubar o preço. Aqui não há problema — e é bom saber
              quando não há. O ativo menos líquido é o MXRF11, com R$ 18,5 milhões por dia; a posição é{" "}
              <strong className="text-ice">0,03%</strong> disso.
            </p>
            <p>
              A diferença real é de prazo: cripto liquida em minutos, 24 horas por dia; ação e FII na B3, em D+2; Tesouro
              Selic, em D+1. Nada disso pesa numa carteira de R$ 120 mil.
            </p>
          </div>
        </div>
      </Section>

      <Section
        heading={
          <>
            O que essa análise <Gold>não</Gold> é
          </>
        }
      >
        <Card className="max-w-3xl space-y-4 text-ice-70">
          <p>
            Não é uma recomendação. A leitura mostra que há 38% em Bitcoin; não diz para vender Bitcoin. Mostra que a
            carteira se move 96% junto com ele; não diz que isso é errado — há quem queira exatamente isso. Mostra que a pior
            queda foi de 34%; não diz se é aceitável, porque isso depende de quem você é, de quanto tempo tem e para que esse
            dinheiro serve.
          </p>
          <p>
            Dois motivos. Filosofia: a indústria produz recomendação demais e diagnóstico de menos. E regra: no Brasil,
            recomendação individualizada é atividade regulada pela CVM e exige credencial. O raio-x entrega uma leitura
            honesta de risco. O que fazer com ela é seu.
          </p>
          <Disclaimer variant="full" />
        </Card>
      </Section>

      <Section className="border-t border-navy-3">
        <h2>
          Isso, na <Gold>sua</Gold> carteira
        </h2>
        <p className="mt-4 max-w-2xl text-ice-70">
          O Alpherion vai fazer exatamente essa leitura na sua carteira, em segundos, e devolver em português. Quem está na
          lista entra primeiro.
        </p>
        <div className="mt-8">
          <EmailCapture source="raio-x" />
        </div>
      </Section>
    </>
  );
}
