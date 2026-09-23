// Posição derivada em memória (site.md §4.2, §7.4): movimentações + ajustes → quantidade,
// preço médio e custo por ativo. Não é tabela porque os números estão cifrados no banco.
//
// **Preço médio pelo método da Receita Federal:** a compra entra no custo com as taxas
// (custo = qtd × preço + taxas); a venda baixa a quantidade e o custo **pelo preço médio**,
// sem alterar o preço médio; posição zerada recomeça do zero na compra seguinte.
//
// **Ajuste (`position_adjustments`) é a quantidade informada, não uma compra a mais.**
// A importação da B3 traz a posição atual *e* o histórico de negociações; somar as duas
// contaria a mesma ação duas vezes. Então o ajuste, quando existe, dá a quantidade atual
// e prevalece sobre a derivada; o preço médio vem do ajuste se foi informado, senão do
// histórico. Ajuste só com valor (renda fixa, cripto sem quantidade) vira posição por valor.
//
// Aritmética em escala inteira (10⁻¹⁰), para não acumular erro de ponto flutuante em
// quantidade fracionária de cripto e em preço com seis casas.

const SCALE = BigInt("10000000000"); // 10 casas
// `BigInt(0)` e não o literal: o tsconfig mira ES2017, que não tem literal de BigInt.
const ZERO = BigInt(0);

export type TransactionInput = {
  assetId: string;
  date: string; // YYYY-MM-DD
  side: "buy" | "sell";
  quantity: string;
  price: string;
  fees?: string | null;
};

export type AdjustmentInput = {
  assetId: string;
  quantity?: string | null;
  valueBrl?: string | null;
  avgPrice?: string | null;
};

export type Position = {
  assetId: string;
  /** Quantidade; `null` quando a posição é só por valor. */
  quantity: string | null;
  /** Preço médio (Receita); `null` quando não há como saber (ajuste sem preço, sem histórico). */
  avgPrice: string | null;
  /** Custo total = quantidade × preço médio. */
  cost: string | null;
  /** Posição informada por valor em reais (sem quantidade). */
  valueBrl: string | null;
  warnings: string[];
};

function toScaled(value: string | null | undefined): bigint | null {
  if (value === null || value === undefined || value.trim() === "") return null;
  const text = value.trim();
  const match = /^(-)?(\d+)(?:\.(\d+))?$/.exec(text);
  if (!match) throw new Error(`número inválido: ${value}`);
  const [, sign, int, frac = ""] = match;
  const fraction = (frac + "0000000000").slice(0, 10);
  const scaled = BigInt(int) * SCALE + BigInt(fraction);
  return sign ? -scaled : scaled;
}

function fromScaled(value: bigint, digits = 10): string {
  const negative = value < ZERO;
  const abs = negative ? -value : value;
  const int = abs / SCALE;
  let frac = (abs % SCALE).toString().padStart(10, "0").slice(0, digits);
  frac = frac.replace(/0+$/, "");
  return `${negative ? "-" : ""}${int}${frac ? `.${frac}` : ""}`;
}

/** a × b em escala. */
const mul = (a: bigint, b: bigint): bigint => (a * b) / SCALE;
/** a ÷ b em escala (b ≠ 0). */
const div = (a: bigint, b: bigint): bigint => (a * SCALE) / b;

type State = { quantity: bigint; cost: bigint; warnings: string[] };

export function derivePositions(transactions: TransactionInput[], adjustments: AdjustmentInput[] = []): Position[] {
  const states = new Map<string, State>();
  const ordered = [...transactions].sort((a, b) => (a.date === b.date ? (a.side === "buy" ? -1 : 1) : a.date < b.date ? -1 : 1));

  for (const tx of ordered) {
    const state = states.get(tx.assetId) ?? { quantity: ZERO, cost: ZERO, warnings: [] };
    const quantity = toScaled(tx.quantity) ?? ZERO;
    const price = toScaled(tx.price) ?? ZERO;
    const fees = toScaled(tx.fees) ?? ZERO;
    if (quantity <= ZERO) {
      state.warnings.push(`${tx.date}: movimentação com quantidade não positiva ignorada`);
    } else if (tx.side === "buy") {
      state.quantity += quantity;
      state.cost += mul(quantity, price) + fees;
    } else if (state.quantity === ZERO) {
      state.warnings.push(`${tx.date}: venda sem posição anterior (histórico incompleto?)`);
    } else {
      const sold = quantity > state.quantity ? state.quantity : quantity;
      if (quantity > state.quantity) {
        state.warnings.push(`${tx.date}: venda maior que a posição; considerada até zerar`);
      }
      const average = div(state.cost, state.quantity);
      state.quantity -= sold;
      state.cost = state.quantity === ZERO ? ZERO : state.cost - mul(sold, average);
    }
    states.set(tx.assetId, state);
  }

  const byAsset = new Map<string, AdjustmentInput>(adjustments.map((a) => [a.assetId, a]));
  const assetIds = new Set([...states.keys(), ...byAsset.keys()]);
  const positions: Position[] = [];

  for (const assetId of assetIds) {
    const state = states.get(assetId) ?? { quantity: ZERO, cost: ZERO, warnings: [] };
    const adjustment = byAsset.get(assetId);
    const derivedAverage = state.quantity > ZERO ? div(state.cost, state.quantity) : null;

    if (adjustment) {
      const quantity = toScaled(adjustment.quantity);
      const valueBrl = toScaled(adjustment.valueBrl);
      if (quantity === null && valueBrl !== null) {
        positions.push({ assetId, quantity: null, avgPrice: null, cost: null, valueBrl: fromScaled(valueBrl, 2), warnings: state.warnings });
        continue;
      }
      if (quantity !== null) {
        const informed = toScaled(adjustment.avgPrice);
        const average = informed ?? derivedAverage;
        if (quantity === ZERO) continue;
        positions.push({
          assetId,
          quantity: fromScaled(quantity),
          avgPrice: average === null ? null : fromScaled(average, 6),
          cost: average === null ? null : fromScaled(mul(quantity, average), 2),
          valueBrl: null,
          warnings: state.warnings,
        });
        continue;
      }
    }

    if (state.quantity === ZERO) continue;
    positions.push({
      assetId,
      quantity: fromScaled(state.quantity),
      avgPrice: derivedAverage === null ? null : fromScaled(derivedAverage, 6),
      cost: fromScaled(state.cost, 2),
      valueBrl: null,
      warnings: state.warnings,
    });
  }

  return positions.sort((a, b) => (a.assetId < b.assetId ? -1 : 1));
}
