const createDraftButton =
    document.getElementById("createDraft");

const lobby =
    document.getElementById("lobby");

const room =
    document.getElementById("room");

const playerName =
    document.getElementById("playerName");

const playerCount =
    document.getElementById("playerCount");

const roomCode =
    document.getElementById("roomCode");

const players =
    document.getElementById("players");

const roomStatus =
    document.getElementById("roomStatus");

const startDraft =
    document.getElementById("startDraft");


createDraftButton.addEventListener("click", () => {

    const name = playerName.value.trim();

    if (!name) {
        alert("Digite seu nome.");
        return;
    }

    const numberOfPlayers =
        Number(playerCount.value);

    const code =
        generateRoomCode();

    lobby.hidden = true;
    room.hidden = false;

    roomCode.textContent = code;

    roomStatus.textContent =
        `Aguardando jogadores... 1/${numberOfPlayers}`;

    players.innerHTML = "";

    addPlayer(name);

    for (
        let i = 1;
        i < numberOfPlayers;
        i++
    ) {

        const emptyPlayer =
            document.createElement("div");

        emptyPlayer.className = "player";

        emptyPlayer.innerHTML = `
            <div class="player-name">
                Jogador ${i + 1}
            </div>

            <div class="player-status">
                Aguardando...
            </div>
        `;

        players.appendChild(emptyPlayer);
    }

});


startDraft.addEventListener("click", () => {

    alert(
        "Aqui entraremos com o motor multiplayer do draft."
    );

});


function addPlayer(name) {

    const element =
        document.createElement("div");

    element.className =
        "player connected";

    element.innerHTML = `
        <div class="player-name">
            ${escapeHtml(name)}
        </div>

        <div class="player-status">
            🟢 Conectado
        </div>
    `;

    players.appendChild(element);
}


function generateRoomCode() {

    const characters =
        "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

    let result = "";

    for (let i = 0; i < 6; i++) {

        result +=
            characters[
                Math.floor(
                    Math.random() *
                    characters.length
                )
            ];

    }

    return result;
}


function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}