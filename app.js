const SUPABASE_URL = "https://xpqeshatbzjqglngdztz.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_1INZjWT0SJFxSVZPUiFrRw_dWcVWC6c";

const supabaseClient = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);

console.log("Supabase conectado:", supabaseClient);

async function initializeAuth() {
    const { data, error } =
        await supabaseClient.auth.signInAnonymously();

    if (error) {
        console.error("Erro na autenticação:", error);
        return null;
    }

    console.log(
        "Jogador autenticado:",
        data.user.id
    );

    return data.user;
}

initializeAuth();
const createDraftButton =
    document.getElementById("createDraft");

const joinDraftButton =
    document.getElementById("joinDraft");

const joinPlayerName =
    document.getElementById("joinPlayerName");

const joinRoomCode =
    document.getElementById("joinRoomCode");

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
    let currentDraftId = null;
    let realtimeChannel = null;
    let currentPlayerId = null;
    let currentIsHost = false;

const startDraft =
    document.getElementById("startDraft");

const orderPanel =
    document.getElementById("orderPanel");

const orderPlayers =
    document.getElementById("orderPlayers");

const saveOrder =
    document.getElementById("saveOrder");

createDraftButton.addEventListener("click", async () => {

    const name = playerName.value.trim();
    const numberOfPlayers = Number(playerCount.value);

    if (!name) {
        alert("Digite seu nome.");
        return;
    }

    createDraftButton.disabled = true;
    createDraftButton.textContent = "Criando sala...";

    try {

        const { data, error } = await supabaseClient.rpc(
            "create_draft",
            {
                p_player_name: name,
                p_player_count: numberOfPlayers
            }
        );

        if (error) {
            console.error("Erro ao criar sala:", error);
            alert("Não foi possível criar a sala.");
            return;
        }

        console.log("Sala criada:", data);

        const draft = data.draft;
        const player = data.player;
        currentDraftId = draft.id;
        currentPlayerId= player.id;
        currentIsHost = true;

        lobby.hidden = true;
        room.hidden = false;

        roomCode.textContent = draft.code;

        roomStatus.textContent =
            `Aguardando jogadores... 1/${draft.player_count}`;

        players.innerHTML = "";

        addPlayer(player.name);

console.log("Antes do loadPlayers");

loadPlayers();

console.log("Depois do loadPlayers");

console.log("Antes do subscribeToPlayers");

subscribeToPlayers();

console.log("Depois do subscribeToPlayers");

    } catch (error) {

        console.error("Erro inesperado:", error);
        alert("Ocorreu um erro ao criar a sala.");

    } finally {

        createDraftButton.disabled = false;
        createDraftButton.textContent = "Criar sala";

    }

});

joinDraftButton.addEventListener("click", async () => {

    const name = joinPlayerName.value.trim();
    const code = joinRoomCode.value.trim().toUpperCase();

    if (!name) {
        alert("Digite seu nome.");
        return;
    }

    if (code.length !== 6) {
        alert("Digite um código de sala válido.");
        return;
    }

    joinDraftButton.disabled = true;
    joinDraftButton.textContent = "Entrando...";

    try {

        const { data, error } = await supabaseClient.rpc(
            "join_draft",
            {
                p_code: code,
                p_player_name: name
            }
        );

        if (error) {
            console.error("Erro ao entrar na sala:", error);
            alert(error.message);
            return;
        }

        console.log("Entrou na sala:", data);

        const draft = data.draft;
        const player = data.player;
        currentDraftId = draft.id;
        currentPlayerId = player.id;
        currentIsHost = false;

        lobby.hidden = true;
        room.hidden = false;

        roomCode.textContent = draft.code;

        roomStatus.textContent =
            `Aguardando jogadores...`;

        players.innerHTML = "";

        addPlayer(player.name);
        loadPlayers();
        subscribeToPlayers();

    } catch (error) {

        console.error("Erro inesperado:", error);
        alert("Ocorreu um erro ao entrar na sala.");

    } finally {

        joinDraftButton.disabled = false;
        joinDraftButton.textContent = "Entrar na sala";

    }

});

startDraft.addEventListener("click", () => {

    alert(
        "Aqui entraremos com o motor multiplayer do draft."
    );

});

async function loadPlayers() {

    if (!currentDraftId) {
        return;
    }

    const { data, error } = await supabaseClient
        .from("players")
        .select("*")
        .eq("draft_id", currentDraftId)
        .order("joined_at", { ascending: true });

    if (error) {
        console.error(
            "Erro ao carregar jogadores:",
            error
        );
        return;
    }

    players.innerHTML = "";

    data.forEach(player => {

        const element =
            document.createElement("div");

        element.className = "player connected";

        element.innerHTML = `
            <div class="player-name">
                ${escapeHtml(player.name)}
            </div>

            <div class="player-status">
                🟢 Conectado
            </div>
        `;

        players.appendChild(element);

    });

    roomStatus.textContent =
        `Jogadores: ${data.length}/${await getPlayerCount()}`;

    // Mostrar painel de ordem somente para o host
    if (currentIsHost) {

        orderPanel.hidden = false;

        renderOrderPlayers(data);

    } else {

        orderPanel.hidden = true;

    }
}

async function getPlayerCount() {

    if (!currentDraftId) {
        return "?";
    }

    const { data, error } = await supabaseClient
        .from("drafts")
        .select("player_count")
        .eq("id", currentDraftId)
        .single();

    if (error) {
        console.error(
            "Erro ao obter quantidade de jogadores:",
            error
        );

        return "?";
    }

    return data.player_count;
}

function renderOrderPlayers(playerList) {

    orderPlayers.innerHTML = "";

    playerList.forEach((player, index) => {

        const element =
            document.createElement("div");

        element.className = "order-player";

        element.draggable = true;

        element.dataset.playerId =
            player.id;

        element.innerHTML = `
            <span class="drag-handle">☰</span>

            <span class="order-number">
                ${index + 1}.
            </span>

            <span class="order-name">
                ${escapeHtml(player.name)}
            </span>
        `;

        orderPlayers.appendChild(element);

    });

    enableDragAndDrop();
}

function enableDragAndDrop() {

    let draggedElement = null;

    const elements =
        orderPlayers.querySelectorAll(
            ".order-player"
        );

    elements.forEach(element => {

        element.addEventListener(
            "dragstart",
            () => {

                draggedElement = element;

                element.classList.add(
                    "dragging"
                );

            }
        );

        element.addEventListener(
            "dragend",
            () => {

                element.classList.remove(
                    "dragging"
                );

                draggedElement = null;

            }
        );

        element.addEventListener(
            "dragover",
            event => {

                event.preventDefault();

                if (
                    !draggedElement ||
                    draggedElement === element
                ) {
                    return;
                }

                const rect =
                    element.getBoundingClientRect();

                const middle =
                    rect.top +
                    rect.height / 2;

                if (event.clientY < middle) {

                    orderPlayers.insertBefore(
                        draggedElement,
                        element
                    );

                } else {

                    orderPlayers.insertBefore(
                        draggedElement,
                        element.nextSibling
                    );

                }

            }
        );

    });

    updateOrderNumbers();
}

function updateOrderNumbers() {

    const elements =
        orderPlayers.querySelectorAll(
            ".order-player"
        );

    elements.forEach((element, index) => {

        const number =
            element.querySelector(
                ".order-number"
            );

        number.textContent =
            `${index + 1}.`;

    });
}

saveOrder.addEventListener(
    "click",
    async () => {

        const elements =
            orderPlayers.querySelectorAll(
                ".order-player"
            );

        const playerIds =
            Array.from(elements).map(
                element =>
                    element.dataset.playerId
            );

        if (playerIds.length < 3) {

            alert(
                "É necessário ter pelo menos 3 jogadores."
            );

            return;
        }

        saveOrder.disabled = true;
        saveOrder.textContent =
            "Salvando...";

        try {

            const { error } =
                await supabaseClient.rpc(
                    "set_player_order",
                    {
                        p_draft_id:
                            currentDraftId,

                        p_player_ids:
                            playerIds
                    }
                );

            if (error) {

                console.error(
                    "Erro ao salvar ordem:",
                    error
                );

                alert(error.message);

                return;
            }

            alert(
                "Ordem salva com sucesso!"
            );

            startDraft.disabled = false;

            await loadPlayers();

        } finally {

            saveOrder.disabled = false;

            saveOrder.textContent =
                "Salvar ordem";

        }

    }
);

function subscribeToPlayers() {

    if (!currentDraftId) {
        return;
    }

    if (realtimeChannel) {
        supabaseClient.removeChannel(realtimeChannel);
    }

    realtimeChannel = supabaseClient
        .channel(`draft-${currentDraftId}`)
        .on(
            "postgres_changes",
            {
                event: "*",
                schema: "public",
                table: "players",
                filter: `draft_id=eq.${currentDraftId}`
            },
            payload => {

                console.log(
                    "Atualização de jogadores:",
                    payload
                );

                loadPlayers();
            }
        )
        .subscribe(status => {

            console.log(
                "Realtime:",
                status
            );

        });
}

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