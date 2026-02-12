document.getElementById("buscarBtn").addEventListener("click", async () => {

    const resultadoDiv = document.getElementById("resultado");
    const infoDiv = document.getElementById("info");
    const dias = document.getElementById("periodoSelect").value;

    resultadoDiv.innerHTML = "";
    infoDiv.innerHTML = "Buscando notícias...";

    try {
        const response = await fetch(`/buscar-noticias?dias=${dias}`);
        const data = await response.json();

        infoDiv.innerHTML = `
            Período: ${data.periodo} |
            Total encontrado: ${data.quantidade}
        `;

        data.noticias.forEach(noticia => {

            const card = document.createElement("div");
            card.classList.add("card");

            // 🎯 Pintura por relevância
            if (noticia.relevancia >= 6) {
                card.classList.add("card-high");
            } else if (noticia.relevancia >= 3) {
                card.classList.add("card-medium");
            }

            card.innerHTML = `
                <div class="card-date">${noticia.data}</div>
                <div class="card-title">${noticia.titulo}</div>
                <div class="card-source">${noticia.fonte}</div>
                <div class="card-relevancia">Relevância: ${noticia.relevancia}</div>
                <a href="${noticia.link}" target="_blank" rel="noopener noreferrer">
                    Ler matéria completa →
                </a>
            `;

            resultadoDiv.appendChild(card);
        });

    } catch (error) {
        infoDiv.innerHTML = "Erro ao buscar notícias.";
    }
});
