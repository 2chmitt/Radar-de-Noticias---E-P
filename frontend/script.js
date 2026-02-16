document.addEventListener("DOMContentLoaded", () => {

  const btn = document.getElementById("buscarBtn");
  const select = document.getElementById("periodoSelect");
  const metodoSelect = document.getElementById("metodoSelect");
  const infoDiv = document.getElementById("info");
  const resultDiv = document.getElementById("resultado");

  const endpoint = document.body.getAttribute("data-endpoint");

  btn.addEventListener("click", async () => {

    const dias = parseInt(select.value, 10);
    const metodo = metodoSelect.value;

    resultDiv.innerHTML = "";
    infoDiv.innerHTML = "Buscando notícias...";

    try {

      const resp = await fetch(`${endpoint}?dias=${dias}&metodo=${metodo}`);
      const data = await resp.json();

      infoDiv.innerHTML =
        `${data.tipo} | ${data.periodo} | Método: ${data.metodo} | Total encontrado: ${data.quantidade}`;

      data.noticias.forEach((n) => {

        const card = document.createElement("div");
        card.classList.add("card");

        if (n.relevancia >= 6) card.classList.add("card-high");
        else if (n.relevancia >= 3) card.classList.add("card-medium");

        card.innerHTML = `
          <div class="card-date">${n.data}</div>
          <div class="card-title">${n.titulo}</div>
          <div class="card-source">${n.fonte}</div>
          <div class="card-relevancia">Relevância: ${n.relevancia}</div>
          <a href="${n.link}" target="_blank" rel="noopener noreferrer">
            Ler matéria completa →
          </a>
        `;

        resultDiv.appendChild(card);
      });

    } catch (e) {
      infoDiv.innerHTML = "Erro ao buscar notícias.";
    }

  });

});
