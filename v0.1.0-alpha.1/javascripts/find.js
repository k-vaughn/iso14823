(function () {
  var input = document.getElementById("find-q");
  var dataNode = document.getElementById("sign-index");
  if (!input || !dataNode) return;

  var data = JSON.parse(dataNode.textContent);
  var category = document.getElementById("find-category");
  var status = document.getElementById("find-status");
  var country = document.getElementById("find-country");
  var count = document.getElementById("find-count");
  var results = document.getElementById("find-results");

  data.categories.forEach(function (item) {
    var option = document.createElement("option");
    option.value = item.code;
    option.textContent = item.code + " " + item.name;
    category.appendChild(option);
  });
  data.countries.forEach(function (item) {
    var option = document.createElement("option");
    option.value = item.code;
    option.textContent = item.name;
    country.appendChild(option);
  });

  var params = new URLSearchParams(window.location.search);
  if (params.get("q")) input.value = params.get("q");
  if (params.get("category")) category.value = params.get("category");
  if (params.has("status")) status.value = params.get("status");
  if (params.get("country")) country.value = params.get("country");

  function compact(value) {
    return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
  }

  function matches(sign, query, queryCompact) {
    if (category.value && sign.service !== category.value) return false;
    if (status.value === "C" || status.value === "D") {
      if (sign.status !== status.value) return false;
    } else if (status.value && sign.kind !== status.value) {
      return false;
    }
    if (country.value && sign.countries.indexOf(country.value) === -1) return false;
    if (!query) return true;
    var hay = [sign.id, sign.code5, sign.name, sign.definition, sign.vienna, sign.notes, sign.serviceName]
      .join("\n")
      .toLowerCase();
    if (hay.indexOf(query) !== -1) return true;
    if (queryCompact.length < 2) return false;
    return compact(hay).indexOf(queryCompact) !== -1;
  }

  function rank(sign, query, queryCompact) {
    if (!query) return 2;
    if (sign.id.toLowerCase() === query || sign.code5 === queryCompact) return 0;
    if (sign.id.toLowerCase().indexOf(query) === 0 || (sign.name || "").toLowerCase().indexOf(query) === 0) {
      return 1;
    }
    return 2;
  }

  function chip(className, label) {
    var node = document.createElement("span");
    node.className = "chip " + className;
    node.textContent = label;
    return node;
  }

  function chipsFor(sign) {
    var wrap = document.createElement("span");
    if (sign.kind === "reserved") wrap.appendChild(chip("chip-reserved", "Reserved"));
    if (sign.kind === "range") wrap.appendChild(chip("chip-range", "Code range"));
    if (sign.status === "C" && sign.kind !== "reserved") wrap.appendChild(chip("chip-current", "Current"));
    if (sign.status === "D") wrap.appendChild(chip("chip-deprecated", "Deprecated"));
    if (sign.draft) {
      var link = document.createElement("a");
      link.className = "chip chip-draft";
      link.href = "../#draft-watermark";
      link.textContent = "Draft";
      wrap.appendChild(link);
    }
    return wrap;
  }

  function shorten(text) {
    var value = (text || "").replace(/\s+/g, " ").trim();
    if (value.length <= 180) return value;
    return value.slice(0, 180).replace(/\s+\S*$/, "") + "…";
  }

  function render() {
    var query = input.value.trim().toLowerCase();
    var queryCompact = compact(query);
    var hits = data.signs.filter(function (sign) {
      return matches(sign, query, queryCompact);
    });
    hits.sort(function (left, right) {
      var order = rank(left, query, queryCompact) - rank(right, query, queryCompact);
      if (order !== 0) return order;
      return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
    });
    var noun = hits.length === 1 ? "sign" : "signs";
    count.textContent = hits.length + " " + noun;
    results.replaceChildren();
    hits.forEach(function (sign) {
      var link = document.createElement("a");
      link.className = "find-hit";
      link.href = "../signs/" + sign.id + "/";
      var code = document.createElement("span");
      code.className = "find-code";
      code.textContent = sign.id;
      var title = document.createElement("span");
      title.className = "find-title";
      title.textContent = sign.name;
      title.appendChild(document.createTextNode(" "));
      title.appendChild(chipsFor(sign));
      link.appendChild(code);
      link.appendChild(title);
      var definition = shorten(sign.definition);
      if (definition && definition !== sign.name) {
        var body = document.createElement("span");
        body.className = "find-def";
        body.textContent = definition;
        link.appendChild(body);
      }
      results.appendChild(link);
    });
  }

  input.addEventListener("input", render);
  category.addEventListener("change", render);
  status.addEventListener("change", render);
  country.addEventListener("change", render);
  input.addEventListener("keydown", function (event) {
    if (event.key !== "Enter") return;
    var first = results.querySelector("a");
    if (first) window.location.href = first.href;
  });
  render();
})();
