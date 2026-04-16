(function () {
  const atlasMap = document.getElementById("atlas-map");
  if (!atlasMap || !window.d3) {
    return;
  }

  const d3 = window.d3;
  const topojson = window.topojson;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STORAGE_KEY = "land-interface-ledger-v1";
  const WORLD_ATLAS_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";
  const REGION_BOUNDS = [
    [33.5, 27.2],
    [45.2, 33.8],
  ];

  const places = [
    {
      id: "hebron",
      name: "Hebron",
      region: "Judean hills",
      status: "historical",
      lat: 31.5326,
      lon: 35.0998,
      offsetDesktop: [18, -18],
      offsetMobile: [12, -16],
      blurb:
        "Promise starts somewhere you can point to. The patriarch story is attached to burial, land, and a city that still exists.",
      jewishContext:
        "Hebron is tied to the patriarchs and to the Cave of Machpelah remembered in Jewish tradition as an ancestral burial place.",
      christianReading:
        "Christians often read Hebron as part of the long covenant line that eventually narrows toward David and then Jesus.",
      historicalNote:
        "The city is ancient and continuously inhabited, though each sacred claim inside it carries layers of later memory and contest.",
    },
    {
      id: "beersheba",
      name: "Beersheba",
      region: "Negev edge",
      status: "historical",
      lat: 31.2529,
      lon: 34.7913,
      offsetDesktop: [-116, 16],
      offsetMobile: [-86, 12],
      blurb:
        "Wells, oath-making, and borders make Beersheba feel like covenant language grounded in a frontier landscape.",
      jewishContext:
        "Beersheba marks a southern threshold in the Hebrew Bible and is remembered through wells, oaths, and patriarchal movement.",
      christianReading:
        "In Christian typology, boundary and promise language here becomes part of the inherited story Jesus enters rather than replaces.",
      historicalNote:
        "The site is archaeologically important and widely identified, even if every biblical scene tied to it cannot be pinned down exactly.",
    },
    {
      id: "bethel",
      name: "Bethel / Beitin",
      region: "Central highlands",
      status: "traditional",
      lat: 31.9411,
      lon: 35.2609,
      offsetDesktop: [18, -18],
      offsetMobile: [14, -18],
      blurb:
        "Bethel turns presence into place. The phrase 'house of God' lands on actual terrain before it becomes metaphor.",
      jewishContext:
        "Bethel is bound to Jacob's vision and to a long memory of encounter, altar, and contested worship.",
      christianReading:
        "Christians often read Bethel as early house-of-God language that later echoes through temple and incarnation themes.",
      historicalNote:
        "The common identification with Beitin is traditional and plausible, though the archaeological conversation is not fully settled.",
    },
    {
      id: "bethlehem",
      name: "Bethlehem",
      region: "South of Jerusalem",
      status: "historical",
      lat: 31.7054,
      lon: 35.2024,
      offsetDesktop: [18, 24],
      offsetMobile: [14, 22],
      blurb:
        "Bethlehem compresses memory of Davidic kingship and messianic expectation into one small town south of Jerusalem.",
      jewishContext:
        "Bethlehem is remembered above all through David and royal expectation within Israel's story.",
      christianReading:
        "For Christians, Bethlehem becomes a deliberate king-town coordinate rather than a decorative nativity backdrop.",
      historicalNote:
        "The town's location is secure, while individual sacred spots inside it are often preserved through later church tradition.",
    },
    {
      id: "sinai",
      name: "Jebel Musa / Sinai",
      region: "South Sinai",
      status: "traditional",
      lat: 28.5397,
      lon: 34.329,
      offsetDesktop: [16, -18],
      offsetMobile: [12, -18],
      blurb:
        "Wilderness is not empty space here. Sinai becomes the place where covenant, law, fear, and presence are fused together.",
      jewishContext:
        "Sinai stands at the center of Jewish covenant memory as the place of revelation and Torah.",
      christianReading:
        "Christian readings often use Sinai as the indispensable backdrop for later mountain, covenant, and presence imagery.",
      historicalNote:
        "Jebel Musa is the classic traditional identification, but the exact mountain of the biblical account remains debated.",
    },
    {
      id: "kadesh",
      name: "Kadesh Barnea",
      region: "Northern Sinai / Negev threshold",
      status: "debated",
      lat: 30.6186,
      lon: 34.4371,
      offsetDesktop: [18, 22],
      offsetMobile: [14, 18],
      blurb:
        "Kadesh is a threshold place: near enough to promise to see it, unstable enough to keep wandering.",
      jewishContext:
        "Kadesh belongs to the wilderness memory of testing, delay, rebellion, and border-crossing failure.",
      christianReading:
        "It helps Christians visualize why later wilderness scenes feel like more than individual temptation stories.",
      historicalNote:
        "The standard identification is approximate and the broader Kadesh zone remains archaeologically debated.",
    },
    {
      id: "jordan",
      name: "Bethany Beyond the Jordan",
      region: "Jordan crossing",
      status: "traditional",
      lat: 31.8376,
      lon: 35.5538,
      offsetDesktop: [20, -18],
      offsetMobile: [14, -18],
      blurb:
        "Crossing water and entering the land becomes one thread. Baptism later reactivates that memory at the river's edge.",
      jewishContext:
        "The Jordan is bound to entry, crossing, inheritance, and prophetic action in Israel's story.",
      christianReading:
        "Christian tradition reads baptism here against Joshua's crossing, new beginning, and preparation imagery.",
      historicalNote:
        "The broad baptismal zone is ancient in memory, but the exact pinpoint is preserved mainly through tradition.",
    },
    {
      id: "nazareth",
      name: "Nazareth",
      region: "Lower Galilee",
      status: "historical",
      lat: 32.6996,
      lon: 35.3035,
      offsetDesktop: [-106, -12],
      offsetMobile: [-82, -14],
      blurb:
        "Nazareth lets the book begin in an ordinary hillside town, which makes the argument feel embodied instead of monumental.",
      jewishContext:
        "Nazareth sits inside the lived world of first-century Jewish Galilee rather than in a mythic nowhere.",
      christianReading:
        "Christians read Nazareth as the hidden, local, and ordinary beginning of a messianic story that later opens outward.",
      historicalNote:
        "Nazareth is well-established as a real Galilean settlement of the period even if later sacred stops within it vary in certainty.",
    },
    {
      id: "cana",
      name: "Cana / Kafr Kanna",
      region: "Galilee",
      status: "traditional",
      lat: 32.746,
      lon: 35.3429,
      offsetDesktop: [18, 20],
      offsetMobile: [14, 18],
      blurb:
        "Cana gives the interface a village scale. Table, joy, and sign-language belong in the same geography as covenant memory.",
      jewishContext:
        "Cana belongs to the fabric of Galilean Jewish life rather than to the major symbolic centers alone.",
      christianReading:
        "Christians often use Cana to connect wedding, abundance, and transformation to a deeply local setting.",
      historicalNote:
        "Kafr Kanna is the classic traditional identification, though other candidates have been proposed.",
    },
    {
      id: "capernaum",
      name: "Capernaum",
      region: "Sea of Galilee",
      status: "historical",
      lat: 32.8803,
      lon: 35.5735,
      offsetDesktop: [18, -20],
      offsetMobile: [14, -18],
      blurb:
        "Capernaum ties teaching, table, healing, and lake geography together. Galilee becomes a real social world, not scenic filler.",
      jewishContext:
        "Capernaum sits inside a network of Jewish villages, synagogues, fishing labor, and Roman pressure around the lake.",
      christianReading:
        "Christian readers often treat it as a kind of ministry base where kingdom language becomes public and local at once.",
      historicalNote:
        "The site is securely identified and heavily studied, though specific built remains are layered across time.",
    },
    {
      id: "bethany",
      name: "Bethany",
      region: "East of Jerusalem",
      status: "traditional",
      lat: 31.7715,
      lon: 35.2622,
      offsetDesktop: [18, 18],
      offsetMobile: [14, 16],
      blurb:
        "Bethany turns the final approach to Jerusalem into a threshold scene rather than a sudden arrival.",
      jewishContext:
        "Bethany belongs to the slope-and-valley geography around Jerusalem that shaped pilgrimage and entry.",
      christianReading:
        "Christian readings often use Bethany as the near edge of passion-week movement, friendship, and approach.",
      historicalNote:
        "The village identification is longstanding, though exact locations of later memorial sites are traditional.",
    },
    {
      id: "jerusalem",
      name: "Jerusalem",
      region: "Hill city",
      status: "historical",
      lat: 31.778,
      lon: 35.2354,
      offsetDesktop: [-104, -10],
      offsetMobile: [-78, -12],
      blurb:
        "Jerusalem is where festival, temple, kingship, sacrifice, exile memory, and modern contest are all forced into one coordinate.",
      jewishContext:
        "Jerusalem is the city of temple memory, pilgrimage, kingship, prayer, and return in Jewish life.",
      christianReading:
        "For Christians it becomes the site where the last week, crucifixion, resurrection memory, and temple re-reading converge.",
      historicalNote:
        "The city itself is secure; particular sacred spots within it often combine archaeology, liturgy, and tradition.",
    },
    {
      id: "emmaus",
      name: "Emmaus",
      region: "Judean foothills",
      status: "debated",
      lat: 31.8397,
      lon: 34.9817,
      offsetDesktop: [-104, -8],
      offsetMobile: [-82, -10],
      blurb:
        "Emmaus gives the resurrection story a road, a meal, and a debated destination. Recognition happens in motion.",
      jewishContext:
        "Emmaus belongs to the hill-country roads west of Jerusalem and to the ordinary geography of departure and return.",
      christianReading:
        "Christians often see Emmaus as the place where scripture, travel, and table suddenly meet in recognition.",
      historicalNote:
        "Emmaus is one of the better examples of a beloved but debated identification, with multiple proposed locations.",
    },
    {
      id: "babylon",
      name: "Babylon",
      region: "Mesopotamia",
      status: "historical",
      lat: 32.5364,
      lon: 44.4202,
      offsetDesktop: [18, -16],
      offsetMobile: [12, -16],
      blurb:
        "A real book about Israel cannot stop at the land alone. Exile must appear on the map or the return theme becomes sentimental.",
      jewishContext:
        "Babylon is exile, displacement, and survival. It is one of the decisive coordinates of Jewish memory.",
      christianReading:
        "Christian readings often turn Babylon into a symbol too quickly. Keeping it on the map prevents that flattening.",
      historicalNote:
        "Babylon is a secure historical site and an essential geographic anchor for exile-return language.",
    },
  ];

  const scenes = [
    {
      id: "promise",
      label: "Promise",
      caption: "Promise begins with wells, altars, burial caves, and a future king-town.",
      primary: "hebron",
      placeIds: ["hebron", "beersheba", "bethel", "bethlehem"],
      routePlaceIds: ["hebron", "beersheba", "bethel", "bethlehem"],
      labelIds: ["hebron", "beersheba", "bethel", "bethlehem"],
      mobileLabelIds: ["hebron", "bethlehem"],
    },
    {
      id: "wilderness",
      label: "Wilderness",
      caption: "Wilderness is not empty. It is the training ground between slavery, covenant, crossing, and entry.",
      primary: "sinai",
      placeIds: ["sinai", "kadesh", "jordan"],
      routePlaceIds: ["sinai", "kadesh", "jordan"],
      labelIds: ["sinai", "kadesh", "jordan"],
      mobileLabelIds: ["sinai", "jordan"],
    },
    {
      id: "galilee",
      label: "Galilee",
      caption: "Jesus emerges in ordinary Galilean towns before the story narrows toward Jerusalem.",
      primary: "nazareth",
      placeIds: ["nazareth", "cana", "capernaum", "jordan"],
      routePlaceIds: ["jordan", "nazareth", "cana", "capernaum"],
      labelIds: ["nazareth", "cana", "capernaum", "jordan"],
      mobileLabelIds: ["nazareth", "capernaum"],
    },
    {
      id: "jerusalem",
      label: "Jerusalem",
      caption: "The final approach gathers village, city, temple, road, meal, and recognition into one dense corridor.",
      primary: "jerusalem",
      placeIds: ["bethany", "jerusalem", "emmaus", "bethlehem"],
      routePlaceIds: ["bethlehem", "bethany", "jerusalem", "emmaus"],
      labelIds: ["bethany", "jerusalem", "emmaus", "bethlehem"],
      mobileLabelIds: ["jerusalem", "emmaus"],
    },
    {
      id: "exile",
      label: "Exile & Return",
      caption: "Without Babylon on the map, return becomes a slogan. Exile has to remain visible to make restoration meaningful.",
      primary: "babylon",
      placeIds: ["jerusalem", "babylon", "nazareth"],
      routePlaceIds: ["jerusalem", "babylon", "jerusalem", "nazareth"],
      labelIds: ["jerusalem", "babylon", "nazareth"],
      mobileLabelIds: ["jerusalem", "babylon"],
    },
  ];

  const themes = [
    {
      id: "promise",
      label: "Promise",
      copy:
        "Promise is not an abstraction here. It is anchored to Hebron, Beersheba, Bethel, and Bethlehem so covenant language stays attached to terrain.",
      note:
        "When the reader can see promise mapped as a route instead of only read as a doctrine, the argument feels discovered rather than declared.",
      placeIds: ["hebron", "beersheba", "bethel", "bethlehem"],
    },
    {
      id: "wilderness",
      label: "Wilderness",
      copy:
        "Sinai, Kadesh, and the Jordan keep wilderness from becoming generic struggle language. It stays a specific corridor of testing and transition.",
      note:
        "This is one of the strongest places where Jesus can be read as reliving Israel's story-patterns rather than floating above them.",
      placeIds: ["sinai", "kadesh", "jordan"],
    },
    {
      id: "kingdom",
      label: "Kingdom",
      copy:
        "Bethlehem, Nazareth, and Jerusalem let kingdom language move from Davidic expectation to public ministry to royal-city collision.",
      note:
        "A map makes kingship less abstract because it shows how local, small-scale, and politically charged these places actually are.",
      placeIds: ["bethlehem", "nazareth", "jerusalem"],
    },
    {
      id: "presence",
      label: "Presence",
      copy:
        "Bethel, Sinai, and Jerusalem form a presence thread: house of God, mountain revelation, and temple city.",
      note:
        "This is where the book can ask whether Jesus is read as carrying Israel's God-presence into ordinary places rather than only referencing it.",
      placeIds: ["bethel", "sinai", "jerusalem"],
    },
    {
      id: "exile",
      label: "Exile",
      copy:
        "Jerusalem and Babylon belong in the same diagram. Without that, a lot of biblical language about loss, longing, and return loses its pressure.",
      note:
        "Keeping Babylon visible resists the lazy habit of turning exile into a vague metaphor detached from real displacement.",
      placeIds: ["jerusalem", "babylon"],
    },
    {
      id: "return",
      label: "Return",
      copy:
        "Babylon, Jerusalem, Nazareth, and Emmaus create a return pattern that is geographic before it becomes symbolic.",
      note:
        "This is one place where an online book can stage multiple readings side by side instead of pretending one interpretation erased all others.",
      placeIds: ["babylon", "jerusalem", "nazareth", "emmaus"],
    },
    {
      id: "table",
      label: "Table",
      copy:
        "Cana, Capernaum, and Emmaus keep the story from becoming only royal or priestly. Meals, houses, and roads carry revelation too.",
      note:
        "Table scenes are often treated as soft or private. On a map they become public coordinates in the same world as temple and exile.",
      placeIds: ["cana", "capernaum", "emmaus"],
    },
  ];

  const festivals = [
    {
      id: "passover",
      label: "Passover",
      period: "Nisan",
      color: "#d58b6f",
      lat: 31.778,
      lon: 35.2354,
      copy:
        "Passover remembers liberation through a meal, a threshold, and a departure. In Christian reading it becomes a major lens for the last week in Jerusalem.",
      note:
        "Putting it on a clock keeps the interface cyclical. The same feast is agricultural, liturgical, historical, and narrative at once.",
    },
    {
      id: "firstfruits",
      label: "Firstfruits",
      period: "Nisan",
      color: "#d4b86e",
      lat: 31.778,
      lon: 35.2354,
      copy:
        "Firstfruits ties the book to harvest language, first yield, and the opening of a season rather than to a single isolated event.",
      note:
        "This is how the design can feel cosmic without drifting into fantasy. The agricultural year already gives you the architecture.",
    },
    {
      id: "shavuot",
      label: "Shavuot",
      period: "Sivan",
      color: "#8bc0a4",
      lat: 31.778,
      lon: 35.2354,
      copy:
        "Shavuot brings harvest, gathering, and Torah memory together. In Christian reading, Pentecost later amplifies that same city rhythm.",
      note:
        "One feast can hold Jewish and Christian layers without collapsing them, if the interface is honest about whose reading is whose.",
    },
    {
      id: "trumpets",
      label: "Trumpets",
      period: "Tishri",
      color: "#84b0d6",
      lat: 31.778,
      lon: 35.2354,
      copy:
        "Trumpets belongs to awakening, announcement, kingship, and the turning of the year into expectation.",
      note:
        "A radial chart makes anticipation legible. Readers see a signal in time, not only a date on a list.",
    },
    {
      id: "atonement",
      label: "Atonement",
      period: "Tishri",
      color: "#9e93d4",
      lat: 31.778,
      lon: 35.2354,
      copy:
        "Atonement centers mercy, priesthood, cleansing, and access. It is hard to tell that story well without Jerusalem and temple memory staying visible.",
      note:
        "This is why the book needs place and calendar together. Priestly meaning without a city and a season becomes too abstract.",
    },
    {
      id: "tabernacles",
      label: "Tabernacles",
      period: "Tishri",
      color: "#5ea7c6",
      lat: 31.7735,
      lon: 35.2313,
      copy:
        "Tabernacles turns dwelling, pilgrimage, water, light, and temporary shelter into one living festival atmosphere.",
      note:
        "It is one of the richest feasts for this kind of interface because it already feels architectural, processional, and spatial.",
    },
  ];

  const jerusalemLayers = [
    {
      id: "temple",
      label: "Temple memory",
      period: "Temple memory",
      copy:
        "Jerusalem begins here as the city of David and the remembered site of temple presence, pilgrimage, and kingship.",
      note:
        "The city is first a concentration point of prayer, sacrifice, covenant identity, and divine presence.",
    },
    {
      id: "exile",
      label: "Exile memory",
      period: "Exile memory",
      copy:
        "Jerusalem is also the city remembered through destruction, loss, longing, and the pain of being cut off from center.",
      note:
        "A serious interface should let the same coordinate carry grief as well as sanctity.",
    },
    {
      id: "second-temple",
      label: "Second Temple",
      period: "Second Temple period",
      copy:
        "The rebuilt city carries intensified expectation, Roman pressure, temple life, and the political density of first-century Judea.",
      note:
        "This is the layer that lets a reader understand why Gospel-era Jerusalem is already thick with waiting and conflict.",
    },
    {
      id: "gospel",
      label: "Gospel week",
      period: "Gospel-era Jerusalem",
      copy:
        "Procession, temple action, final meal, trial, crucifixion, and resurrection memory all collapse into a short Jerusalem corridor.",
      note:
        "The city becomes an event machine. Every gate, hill, and road matters because the narrative pace tightens inside real streets.",
    },
    {
      id: "modern",
      label: "Modern city",
      period: "Modern Jerusalem",
      copy:
        "Today the city is still sacred, inhabited, argued over, and visible. Readers can leave the essay and open the same place in Maps instantly.",
      note:
        "That move from text to present-day map is what makes the online book feel alive instead of closed inside its own rhetoric.",
    },
  ];

  const sceneById = new Map(scenes.map((scene) => [scene.id, scene]));
  const placeById = new Map(places.map((place) => [place.id, place]));
  const themeById = new Map(themes.map((theme) => [theme.id, theme]));
  const festivalById = new Map(festivals.map((festival) => [festival.id, festival]));
  const focusSceneByPlace = {
    hebron: "promise",
    beersheba: "promise",
    bethel: "promise",
    bethlehem: "promise",
    sinai: "wilderness",
    kadesh: "wilderness",
    jordan: "wilderness",
    nazareth: "galilee",
    cana: "galilee",
    capernaum: "galilee",
    bethany: "jerusalem",
    jerusalem: "jerusalem",
    emmaus: "jerusalem",
    babylon: "exile",
  };

  const orderedPlaceIds = [
    "hebron",
    "beersheba",
    "bethel",
    "bethlehem",
    "sinai",
    "kadesh",
    "jordan",
    "nazareth",
    "cana",
    "capernaum",
    "bethany",
    "jerusalem",
    "emmaus",
    "babylon",
  ];

  const refs = {
    sceneCaption: document.getElementById("scene-caption"),
    sceneTabs: document.getElementById("scene-tabs"),
    placeTitle: document.getElementById("place-title"),
    placeStatus: document.getElementById("place-status"),
    placeRegion: document.getElementById("place-region"),
    placeCopy: document.getElementById("place-copy"),
    placeJewish: document.getElementById("place-jewish"),
    placeChristian: document.getElementById("place-christian"),
    placeHistorical: document.getElementById("place-historical"),
    placeMaps: document.getElementById("place-maps"),
    placeStreet: document.getElementById("place-street"),
    placeScene: document.getElementById("place-scene"),
    placeGrid: document.getElementById("place-grid"),
    ledgerPlaces: document.getElementById("ledger-places"),
    ledgerScenes: document.getElementById("ledger-scenes"),
    ledgerThemes: document.getElementById("ledger-themes"),
    ledgerFeasts: document.getElementById("ledger-feasts"),
    themePills: document.getElementById("theme-pills"),
    themeTitle: document.getElementById("theme-title"),
    themeCopy: document.getElementById("theme-copy"),
    themeNote: document.getElementById("theme-note"),
    echoNetwork: document.getElementById("echo-network"),
    feastClock: document.getElementById("feast-clock"),
    feastTitle: document.getElementById("feast-title"),
    feastCopy: document.getElementById("feast-copy"),
    feastNote: document.getElementById("feast-note"),
    feastMaps: document.getElementById("feast-maps"),
    festivalList: document.getElementById("festival-list"),
    jerusalemStage: document.getElementById("jerusalem-stage"),
    jerusalemPeriod: document.getElementById("jerusalem-period"),
    jerusalemCopy: document.getElementById("jerusalem-copy"),
    jerusalemSlider: document.getElementById("jerusalem-slider"),
    jerusalemTabs: document.getElementById("jerusalem-tabs"),
    jerusalemLayerTitle: document.getElementById("jerusalem-layer-title"),
    jerusalemLayerCopy: document.getElementById("jerusalem-layer-copy"),
    jerusalemLayerNote: document.getElementById("jerusalem-layer-note"),
    jerusalemMaps: document.getElementById("jerusalem-maps"),
  };

  let mapTopology = null;
  let currentProjection = null;
  let routeSelection = null;
  let markerSelection = null;
  let labelSelection = null;
  let activeSceneId = scenes[0].id;
  let activePlaceId = scenes[0].primary;
  let activeThemeId = themes[0].id;
  let activeFestivalId = festivals[0].id;
  let activeJerusalemIndex = 0;

  const ledger = loadLedger();

  buildSceneTabs();
  buildPlaceGrid();
  buildThemePills();
  buildFestivalList();
  buildJerusalemTabs();
  setupRevealObserver();

  setPlace(activePlaceId, { mark: true });
  setScene(activeSceneId, { animate: false, preferredPlaceId: activePlaceId });
  setTheme(activeThemeId);
  setFestival(activeFestivalId);
  setJerusalemLayer(activeJerusalemIndex);
  renderEchoGraph();
  renderFeastClock();
  renderLedger();

  loadMapTopology();
  window.addEventListener(
    "resize",
    debounce(() => {
      renderMap();
      renderEchoGraph();
      renderFeastClock();
    }, 140),
  );

  refs.jerusalemSlider.addEventListener("input", (event) => {
    setJerusalemLayer(Number(event.target.value));
  });

  function buildSceneTabs() {
    refs.sceneTabs.innerHTML = "";
    scenes.forEach((scene) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "scene-tab";
      button.textContent = scene.label;
      button.dataset.sceneId = scene.id;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        setScene(scene.id, { animate: !prefersReducedMotion });
      });
      refs.sceneTabs.appendChild(button);
    });
  }

  function buildPlaceGrid() {
    refs.placeGrid.innerHTML = "";
    orderedPlaceIds.forEach((placeId) => {
      const place = placeById.get(placeId);
      const article = document.createElement("article");
      article.className = "place-card";
      article.dataset.placeId = place.id;
      article.dataset.active = "false";

      const top = document.createElement("div");
      top.className = "place-card-top";

      const titleWrap = document.createElement("div");
      const title = document.createElement("h4");
      title.className = "place-card-title";
      title.textContent = place.name;
      const region = document.createElement("p");
      region.className = "place-card-region";
      region.textContent = place.region;
      titleWrap.append(title, region);

      const badge = document.createElement("span");
      badge.className = "status-badge";
      badge.dataset.status = place.status;
      badge.textContent = statusLabel(place.status);
      top.append(titleWrap, badge);

      const copy = document.createElement("p");
      copy.className = "place-card-copy";
      copy.textContent = place.blurb;

      const actions = document.createElement("div");
      actions.className = "place-card-actions";

      const focusButton = document.createElement("button");
      focusButton.type = "button";
      focusButton.className = "place-card-button";
      focusButton.textContent = "Focus";
      focusButton.addEventListener("click", () => {
        setScene(focusSceneByPlace[place.id] || activeSceneId, {
          animate: !prefersReducedMotion,
          preferredPlaceId: place.id,
        });
      });

      const mapsLink = document.createElement("a");
      mapsLink.className = "place-card-link";
      mapsLink.href = mapsSearchUrl(place.lat, place.lon);
      mapsLink.target = "_blank";
      mapsLink.rel = "noreferrer";
      mapsLink.textContent = "Maps";

      const streetLink = document.createElement("a");
      streetLink.className = "place-card-link";
      streetLink.href = streetViewUrl(place.lat, place.lon);
      streetLink.target = "_blank";
      streetLink.rel = "noreferrer";
      streetLink.textContent = "Street View";

      actions.append(focusButton, mapsLink, streetLink);
      article.append(top, copy, actions);
      refs.placeGrid.appendChild(article);
    });
  }

  function buildThemePills() {
    refs.themePills.innerHTML = "";
    themes.forEach((theme) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "theme-pill";
      button.textContent = theme.label;
      button.dataset.themeId = theme.id;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        setTheme(theme.id);
      });
      refs.themePills.appendChild(button);
    });
  }

  function buildFestivalList() {
    refs.festivalList.innerHTML = "";
    festivals.forEach((festival) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "festival-chip";
      button.textContent = festival.label;
      button.dataset.festivalId = festival.id;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        setFestival(festival.id);
      });
      refs.festivalList.appendChild(button);
    });
  }

  function buildJerusalemTabs() {
    refs.jerusalemTabs.innerHTML = "";
    jerusalemLayers.forEach((layer, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "jerusalem-tab";
      button.textContent = layer.label;
      button.dataset.layerIndex = String(index);
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        refs.jerusalemSlider.value = String(index);
        setJerusalemLayer(index);
      });
      refs.jerusalemTabs.appendChild(button);
    });
  }

  function setScene(sceneId, options = {}) {
    const scene = sceneById.get(sceneId);
    if (!scene) {
      return;
    }

    activeSceneId = scene.id;
    refs.sceneCaption.textContent = scene.caption;
    markLedger("scenes", scene.id);

    refs.sceneTabs.querySelectorAll(".scene-tab").forEach((button) => {
      const isActive = button.dataset.sceneId === scene.id;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });

    const nextPlaceId =
      options.preferredPlaceId && scene.placeIds.includes(options.preferredPlaceId) ? options.preferredPlaceId : scene.primary;
    setPlace(nextPlaceId, { mark: true, silentSceneLink: true });
    syncMapState(options.animate !== false);
    syncPlaceGridState();
  }

  function setPlace(placeId, options = {}) {
    const place = placeById.get(placeId);
    if (!place) {
      return;
    }

    activePlaceId = place.id;
    refs.placeTitle.textContent = place.name;
    refs.placeStatus.dataset.status = place.status;
    refs.placeStatus.textContent = statusLabel(place.status);
    refs.placeRegion.textContent = place.region;
    refs.placeCopy.textContent = place.blurb;
    refs.placeJewish.textContent = place.jewishContext;
    refs.placeChristian.textContent = place.christianReading;
    refs.placeHistorical.textContent = place.historicalNote;
    refs.placeMaps.href = mapsSearchUrl(place.lat, place.lon);
    refs.placeStreet.href = streetViewUrl(place.lat, place.lon);

    const sceneId = focusSceneByPlace[place.id] || activeSceneId;
    const scene = sceneById.get(sceneId);
    refs.placeScene.textContent = scene ? `Scene: ${scene.label}` : "Current scene";
    refs.placeScene.href = "#atlas-title";

    if (!options.silentSceneLink && sceneId !== activeSceneId) {
      setScene(sceneId, { animate: !prefersReducedMotion, preferredPlaceId: place.id });
      return;
    }

    markLedger("places", place.id);
    syncMapState(false);
    syncPlaceGridState();
  }

  function setTheme(themeId) {
    const theme = themeById.get(themeId);
    if (!theme) {
      return;
    }

    activeThemeId = theme.id;
    refs.themeTitle.textContent = theme.label;
    refs.themeCopy.textContent = theme.copy;
    refs.themeNote.textContent = theme.note;
    refs.themePills.querySelectorAll(".theme-pill").forEach((button) => {
      const isActive = button.dataset.themeId === theme.id;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    markLedger("themes", theme.id);
    renderEchoGraph();
  }

  function setFestival(festivalId) {
    const festival = festivalById.get(festivalId);
    if (!festival) {
      return;
    }

    activeFestivalId = festival.id;
    refs.feastTitle.textContent = festival.label;
    refs.feastCopy.textContent = festival.copy;
    refs.feastNote.textContent = festival.note;
    refs.feastMaps.href = mapsSearchUrl(festival.lat, festival.lon);
    refs.festivalList.querySelectorAll(".festival-chip").forEach((button) => {
      const isActive = button.dataset.festivalId === festival.id;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    markLedger("feasts", festival.id);
    renderFeastClock();
  }

  function setJerusalemLayer(index) {
    const layer = jerusalemLayers[index];
    if (!layer) {
      return;
    }

    activeJerusalemIndex = index;
    refs.jerusalemStage.dataset.layer = layer.id;
    refs.jerusalemPeriod.textContent = layer.period;
    refs.jerusalemCopy.textContent = layer.copy;
    refs.jerusalemLayerTitle.textContent = layer.label;
    refs.jerusalemLayerCopy.textContent = layer.copy;
    refs.jerusalemLayerNote.textContent = layer.note;
    refs.jerusalemMaps.href = mapsSearchUrl(31.778, 35.2354);
    refs.jerusalemTabs.querySelectorAll(".jerusalem-tab").forEach((button) => {
      const isActive = Number(button.dataset.layerIndex) === index;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function syncPlaceGridState() {
    refs.placeGrid.querySelectorAll(".place-card").forEach((card) => {
      const isActive = card.dataset.placeId === activePlaceId;
      card.dataset.active = String(isActive);
    });
  }

  function renderLedger() {
    refs.ledgerPlaces.textContent = String(ledger.places.length);
    refs.ledgerScenes.textContent = String(ledger.scenes.length);
    refs.ledgerThemes.textContent = String(ledger.themes.length);
    refs.ledgerFeasts.textContent = String(ledger.feasts.length);
  }

  function markLedger(kind, value) {
    if (!ledger[kind].includes(value)) {
      ledger[kind].push(value);
      persistLedger();
      renderLedger();
    }
  }

  function loadLedger() {
    const base = {
      places: [],
      scenes: [],
      themes: [],
      feasts: [],
    };

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return base;
      }

      const parsed = JSON.parse(raw);
      return {
        places: Array.isArray(parsed.places) ? parsed.places : [],
        scenes: Array.isArray(parsed.scenes) ? parsed.scenes : [],
        themes: Array.isArray(parsed.themes) ? parsed.themes : [],
        feasts: Array.isArray(parsed.feasts) ? parsed.feasts : [],
      };
    } catch (error) {
      return base;
    }
  }

  function persistLedger() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ledger));
    } catch (error) {
      return;
    }
  }

  async function loadMapTopology() {
    try {
      const response = await fetch(WORLD_ATLAS_URL, { mode: "cors" });
      if (!response.ok) {
        throw new Error(`Atlas fetch failed with ${response.status}`);
      }
      mapTopology = await response.json();
    } catch (error) {
      mapTopology = null;
    }

    renderMap();
  }

  function renderMap() {
    const svg = d3.select(atlasMap);
    const stageWidth = atlasMap.parentElement.clientWidth;
    const width = Math.max(320, stageWidth);
    const height = width < 760 ? 520 : 620;
    const extent = width < 760 ? [[42, 38], [width - 42, height - 58]] : [[54, 40], [width - 54, height - 60]];
    const regionFeature = boundsToFeature(REGION_BOUNDS);

    svg.attr("viewBox", `0 0 ${width} ${height}`);
    svg.selectAll("*").remove();

    const defs = svg.append("defs");
    defs
      .append("linearGradient")
      .attr("id", "atlas-sea")
      .attr("x1", "0%")
      .attr("y1", "0%")
      .attr("x2", "100%")
      .attr("y2", "100%")
      .call((gradient) => {
        gradient.append("stop").attr("offset", "0%").attr("stop-color", "#0e1627");
        gradient.append("stop").attr("offset", "100%").attr("stop-color", "#07111d");
      });

    svg.append("rect").attr("width", width).attr("height", height).attr("fill", "url(#atlas-sea)");

    const projection = d3.geoMercator().fitExtent(extent, regionFeature);
    currentProjection = projection;
    const path = d3.geoPath(projection);
    const graticule = d3.geoGraticule().step([2, 2]);

    svg.append("path").datum(graticule()).attr("class", "atlas-grid").attr("d", path);

    if (mapTopology && topojson && mapTopology.objects && mapTopology.objects.countries) {
      const countries = topojson.feature(mapTopology, mapTopology.objects.countries).features;
      const regionalFeatures = countries.filter((feature) => intersectsBounds(d3.geoBounds(feature), REGION_BOUNDS));
      svg.append("g").selectAll("path").data(regionalFeatures).join("path").attr("class", "atlas-land").attr("d", path);
      svg
        .append("path")
        .datum(topojson.mesh(mapTopology, mapTopology.objects.countries, (a, b) => a !== b))
        .attr("class", "atlas-border")
        .attr("d", path);
    }

    routeSelection = svg
      .append("g")
      .selectAll("path")
      .data(scenes)
      .join("path")
      .attr("class", "atlas-route")
      .attr("data-route-id", (scene) => scene.id)
      .attr("d", (scene) => {
        const points = scene.routePlaceIds.map((placeId) => projectPlace(placeId, projection));
        return d3.line().curve(d3.curveCatmullRom.alpha(0.45))(points);
      });

    markerSelection = svg
      .append("g")
      .selectAll("g")
      .data(places)
      .join("g")
      .attr("class", "atlas-marker")
      .attr("data-place-id", (place) => place.id)
      .attr("data-status", (place) => place.status)
      .attr("transform", (place) => {
        const [x, y] = projection([place.lon, place.lat]);
        return `translate(${x}, ${y})`;
      })
      .each(function (place) {
        const group = d3.select(this);
        group
          .append("circle")
          .attr("class", "marker-halo")
          .attr("r", 9)
          .attr("opacity", 0.7);
        group.append("circle").attr("class", "marker-core").attr("r", 5.6);
      })
      .attr("role", "button")
      .attr("tabindex", 0)
      .on("click", (_, place) => {
        setPlace(place.id);
      })
      .on("keydown", (event, place) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          setPlace(place.id);
        }
      });

    labelSelection = svg
      .append("g")
      .selectAll("g")
      .data(places)
      .join("g")
      .attr("class", "atlas-label")
      .attr("data-place-id", (place) => place.id)
      .each(function (place) {
        const group = d3.select(this);
        const text = group.append("text");
        text.append("tspan").text(statusLabel(place.status));
        text.append("tspan").attr("x", 0).attr("dy", 16).text(place.name);
      });

    syncMapState(false);
  }

  function syncMapState(animateRoutes) {
    if (!routeSelection || !markerSelection || !labelSelection) {
      return;
    }

    const scene = sceneById.get(activeSceneId);
    const visibleLabels = new Set(window.innerWidth < 760 ? scene.mobileLabelIds : scene.labelIds);
    visibleLabels.add(activePlaceId);

    routeSelection.each(function (routeScene) {
      const path = d3.select(this);
      const isActive = routeScene.id === activeSceneId;
      path.classed("is-active", isActive).classed("is-muted", !isActive);

      if (isActive && animateRoutes && !prefersReducedMotion) {
        const length = this.getTotalLength();
        path.interrupt();
        path.attr("stroke-dasharray", `${length} ${length}`).attr("stroke-dashoffset", length).transition().duration(900).attr("stroke-dashoffset", 0);
      } else {
        path.interrupt();
        path.attr("stroke-dasharray", null).attr("stroke-dashoffset", null);
      }
    });

    markerSelection.each(function (place) {
      const group = d3.select(this);
      const state = place.id === activePlaceId ? "selected" : scene.placeIds.includes(place.id) ? "active" : "muted";
      group.attr("data-state", state);
      group.select(".marker-halo").attr("r", state === "selected" ? 13 : 9).attr("opacity", state === "muted" ? 0.2 : 0.7);
      group.select(".marker-core").attr("r", state === "selected" ? 6.6 : 5.6);
    });

    labelSelection.each(function (place) {
      const group = d3.select(this);
      if (!visibleLabels.has(place.id)) {
        group.attr("display", "none");
        return;
      }

      const point = projectPlace(place.id);
      const offset = window.innerWidth < 760 ? place.offsetMobile : place.offsetDesktop;
      const x2 = point[0] + offset[0];
      const y2 = point[1] + offset[1];
      group.attr("display", null);
      group.selectAll("*").remove();
      group
        .append("line")
        .attr("x1", point[0])
        .attr("y1", point[1])
        .attr("x2", x2)
        .attr("y2", y2);
      const text = group
        .append("text")
        .attr("x", x2)
        .attr("y", y2)
        .attr("text-anchor", offset[0] < 0 ? "end" : "start");
      text.append("tspan").text(statusLabel(place.status));
      text.append("tspan").attr("x", x2).attr("dy", 16).text(place.name);
    });
  }

  function renderEchoGraph() {
    const svg = d3.select(refs.echoNetwork);
    const width = 820;
    const height = 560;
    const activeTheme = themeById.get(activeThemeId);
    const graphPlaceIds = [
      "hebron",
      "sinai",
      "jordan",
      "bethlehem",
      "nazareth",
      "capernaum",
      "jerusalem",
      "emmaus",
      "babylon",
    ];

    const themePositions = new Map();
    const placePositions = new Map();

    themes.forEach((theme, index) => {
      themePositions.set(theme.id, { x: 156, y: 72 + index * 64 });
    });

    graphPlaceIds.forEach((placeId, index) => {
      placePositions.set(placeId, { x: 640, y: 62 + index * 54 });
    });

    svg.attr("viewBox", `0 0 ${width} ${height}`);
    svg.selectAll("*").remove();

    svg
      .append("rect")
      .attr("x", 18)
      .attr("y", 18)
      .attr("width", width - 36)
      .attr("height", height - 36)
      .attr("rx", 18)
      .attr("fill", "rgba(9, 11, 18, 0.16)")
      .attr("stroke", "rgba(224, 193, 123, 0.08)");

    const links = themes.flatMap((theme) =>
      theme.placeIds
        .filter((placeId) => placePositions.has(placeId))
        .map((placeId) => ({
          themeId: theme.id,
          placeId,
          isActive: theme.id === activeThemeId,
        })),
    );

    const linkGroup = svg.append("g");
    linkGroup
      .selectAll("path")
      .data(links)
      .join("path")
      .attr("class", (link) =>
        link.themeId === activeThemeId ? "network-link is-active" : activeTheme.placeIds.includes(link.placeId) ? "network-link" : "network-link is-dim",
      )
      .attr("d", (link) => {
        const from = themePositions.get(link.themeId);
        const to = placePositions.get(link.placeId);
        const c1x = from.x + 150;
        const c2x = to.x - 150;
        return `M ${from.x} ${from.y} C ${c1x} ${from.y}, ${c2x} ${to.y}, ${to.x} ${to.y}`;
      });

    const themeGroup = svg.append("g");
    themeGroup
      .selectAll("g")
      .data(themes)
      .join("g")
      .attr("class", (theme) => `network-node network-node--theme${theme.id === activeThemeId ? " is-active" : ""}`)
      .attr("transform", (theme) => {
        const point = themePositions.get(theme.id);
        return `translate(${point.x}, ${point.y})`;
      })
      .style("cursor", "pointer")
      .on("click", (_, theme) => {
        setTheme(theme.id);
      })
      .each(function (theme) {
        const group = d3.select(this);
        group.append("circle").attr("r", 13);
        group
          .append("text")
          .attr("class", "network-label")
          .attr("x", 24)
          .attr("y", 5)
          .text(theme.label);
      });

    const placeGroup = svg.append("g");
    placeGroup
      .selectAll("g")
      .data(graphPlaceIds.map((placeId) => placeById.get(placeId)))
      .join("g")
      .attr("class", (place) => {
        const isActive = activeTheme.placeIds.includes(place.id);
        return `network-node network-node--place${isActive ? " is-active" : " is-dim"}`;
      })
      .attr("transform", (place) => {
        const point = placePositions.get(place.id);
        return `translate(${point.x}, ${point.y})`;
      })
      .style("cursor", "pointer")
      .on("click", (_, place) => {
        setScene(focusSceneByPlace[place.id] || activeSceneId, {
          animate: !prefersReducedMotion,
          preferredPlaceId: place.id,
        });
      })
      .each(function (place) {
        const group = d3.select(this);
        group.append("circle").attr("r", 11);
        group
          .append("text")
          .attr("class", activeTheme.placeIds.includes(place.id) ? "network-label network-label--place" : "network-label network-label--place network-label--dim")
          .attr("x", -20)
          .attr("y", 5)
          .attr("text-anchor", "end")
          .text(place.name);
      });
  }

  function renderFeastClock() {
    const svg = d3.select(refs.feastClock);
    const size = 520;
    const center = size / 2;
    const activeFestival = festivalById.get(activeFestivalId);
    const pie = d3.pie().sort(null).value(() => 1);
    const arc = d3.arc().innerRadius(118).outerRadius(216);
    const labelArc = d3.arc().innerRadius(240).outerRadius(240);

    svg.attr("viewBox", `0 0 ${size} ${size}`);
    svg.selectAll("*").remove();

    const group = svg.append("g").attr("transform", `translate(${center}, ${center})`);
    group.append("circle").attr("class", "clock-orbit").attr("r", 236);
    group.append("circle").attr("class", "clock-orbit").attr("r", 100);

    const slices = group
      .selectAll("path")
      .data(pie(festivals))
      .join("path")
      .attr("class", (d) => (d.data.id === activeFestivalId ? "feast-slice is-active" : "feast-slice is-dim"))
      .attr("fill", (d) => d.data.color)
      .attr("d", arc)
      .style("opacity", (d) => (d.data.id === activeFestivalId ? 1 : 0.46))
      .on("click", (_, d) => {
        setFestival(d.data.id);
      });

    if (!prefersReducedMotion) {
      slices
        .attr("transform", (d) => (d.data.id === activeFestivalId ? translateArc(d, 8) : translateArc(d, 0)))
        .transition()
        .duration(280)
        .attr("transform", (d) => (d.data.id === activeFestivalId ? translateArc(d, 10) : translateArc(d, 0)));
    } else {
      slices.attr("transform", (d) => (d.data.id === activeFestivalId ? translateArc(d, 10) : translateArc(d, 0)));
    }

    group
      .selectAll("text.feast-label")
      .data(pie(festivals))
      .join("text")
      .attr("class", "feast-label")
      .attr("transform", (d) => {
        const [x, y] = labelArc.centroid(d);
        return `translate(${x}, ${y})`;
      })
      .style("opacity", (d) => (d.data.id === activeFestivalId ? 1 : 0.74))
      .text((d) => d.data.label);

    group.append("circle").attr("class", "clock-center-ring").attr("r", 88);
    group.append("text").attr("class", "clock-center-title").attr("y", -6).text(activeFestival.label);
    group.append("text").attr("class", "clock-center-copy").attr("y", 18).text(activeFestival.period);
    group.append("text").attr("class", "clock-center-copy").attr("y", 36).text("Pilgrim year");
  }

  function translateArc(slice, distance) {
    const angle = (slice.startAngle + slice.endAngle) / 2 - Math.PI / 2;
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;
    return `translate(${x}, ${y})`;
  }

  function projectPlace(placeId, projectionOverride) {
    const place = placeById.get(placeId);
    const projection = projectionOverride || currentProjection;
    if (!projection) {
      return [0, 0];
    }
    return projection([place.lon, place.lat]);
  }

  function boundsToFeature(bounds) {
    const [[west, south], [east, north]] = bounds;
    return {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
      },
    };
  }

  function intersectsBounds(featureBounds, regionBounds) {
    const [[westA, southA], [eastA, northA]] = featureBounds;
    const [[westB, southB], [eastB, northB]] = regionBounds;
    return westA <= eastB && eastA >= westB && southA <= northB && northA >= southB;
  }

  function mapsSearchUrl(lat, lon) {
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
  }

  function streetViewUrl(lat, lon) {
    return `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}`;
  }

  function statusLabel(status) {
    if (status === "historical") {
      return "Historical";
    }
    if (status === "traditional") {
      return "Traditional";
    }
    return "Debated";
  }

  function debounce(fn, wait) {
    let timer = null;
    return function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        fn();
      }, wait);
    };
  }

  function setupRevealObserver() {
    if (prefersReducedMotion) {
      return;
    }

    const items = document.querySelectorAll(".atlas-shell, .jerusalem-shell, .viz-shell, .difference-card");
    if (!items.length) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      items.forEach((item) => item.classList.add("reveal-ready", "is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("reveal-ready", "is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.18,
        rootMargin: "0px 0px -40px 0px",
      },
    );

    items.forEach((item) => {
      item.classList.add("reveal-ready");
      observer.observe(item);
    });
  }
})();
