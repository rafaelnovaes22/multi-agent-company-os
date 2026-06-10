import { chromium } from "playwright";
import * as path from "path";

async function run() {
  console.log("Iniciando navegador Playwright...");
  const browser = await chromium.launch({
    headless: true, // Gravando em modo headless para consistência
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: "./videos/",
      size: { width: 1280, height: 720 },
    },
  });

  const page = await context.newPage();

  const url = "https://acme-multiagentes-314908907992.us-central1.run.app/?key=acme2026";
  console.log(`Navegando para: ${url}`);
  await page.goto(url);

  // Aguarda o redirecionamento e carregamento
  await page.waitForLoadState("networkidle");
  console.log("Página carregada com sucesso.");

  // --- s1_intro (0s - 11.52s) ---
  console.log("Ato 1: Introdução no Hero (11.5s)");
  await page.waitForTimeout(11520);

  // --- s2_ato1 (11.52s - 19.87s) ---
  console.log("Ato 1: O Produto (Painel do Dono) - rolagem para #casos");
  await page.click('a[href="#casos"]');
  await page.waitForTimeout(8350);

  // --- s3_ato2 (19.87s - 29.61s) ---
  console.log("Ato 2: A Escala (Execução Real na Frota) - rolagem para #executar");
  await page.click('a[href="#executar"]');
  await page.waitForTimeout(1000); // espera scroll terminar

  // Digita no formulário de forma natural
  console.log("Preenchendo formulário...");
  const companyInput = page.locator("#x-company");
  await companyInput.click();
  await companyInput.press("Control+A");
  await companyInput.press("Backspace");
  await companyInput.type("Acme Limpeza Enterprise", { delay: 60 });
  await page.waitForTimeout(500);

  // Clica para rodar
  console.log("Clicando em Executar na frota...");
  await page.click("#x-run");
  
  // Aguarda a execução terminar, mostra o trace e clica no auditor do Brain
  await page.waitForTimeout(5240);
  console.log("Clicando em Verificar Eventos no Brain...");
  await page.click("#x-reload-brain");
  await page.waitForTimeout(3000); // total 8.24s desde o clique em rodar

  // --- s4_ato3 (29.61s - 39.67s) ---
  console.log("Ato 3: A Confiança (Gates) - volta para casos e avança slide");
  await page.click('a[href="#casos"]');
  await page.waitForTimeout(1200); // espera scroll
  
  // Clica no botão avançar do carrossel para slide 2 (Confiança)
  await page.click(".arrow-r");
  await page.waitForTimeout(8860); // total 10.06s

  // --- s5_ato4 (39.67s - 54.91s) ---
  console.log("Ato 4: Assinatura Técnica (Execução de Testes) - avança slide 3");
  await page.click(".arrow-r");
  await page.waitForTimeout(15240); // total 15.24s

  // --- s6_fecho (54.91s - 64.34s) ---
  console.log("Fechamento: A Frota de 164 agentes");
  await page.click('a[href="#frota"]');
  await page.waitForTimeout(2000); // espera animação de subida

  // Passa o mouse sobre alguns agentes para abrir tooltips
  console.log("Passando o mouse nos agentes da frota...");
  const agents = page.locator(".agent");
  const count = await agents.count();
  if (count > 0) {
    // Passa o mouse sobre alguns pontos espalhados
    const indices = [15, 42, 88, 120];
    for (const idx of indices) {
      if (idx < count) {
        await agents.nth(idx).hover();
        await page.waitForTimeout(1200);
      }
    }
  }
  await page.waitForTimeout(2630); // total 9.43s

  // --- s7_final (64.34s - 69.70s) ---
  console.log("Ato final: Rodando cubo 3D no rodapé");
  const footer = page.locator("footer");
  await footer.scrollIntoViewIfNeeded();
  await page.waitForTimeout(5350); // total 5.35s

  console.log("Fechando navegador e salvando gravação...");
  await context.close();
  await browser.close();

  console.log("Processo concluído!");
}

run().catch((err) => {
  console.error("Erro na gravação:", err);
  process.exit(1);
});
