// Home provisória da Etapa 1: só o hero do §5. A landing completa entra na Etapa 2.
export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-site flex-1 flex-col justify-center px-4 py-16 md:px-6">
      <h1>
        Você sabe o que <span className="text-gold">tem</span>?
      </h1>
      <p className="mt-6 max-w-2xl text-ice-70">
        O Alpherion lê a sua carteira — cripto, ações, FIIs, renda fixa — e devolve cinco leituras
        de risco, em segundos, em português. Não diz o que comprar.
      </p>
    </main>
  );
}
