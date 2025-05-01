document.addEventListener("DOMContentLoaded", () => {
    let laptops = [];
    let cart = [];
    let selectedLaptop = null;
    let filteredLaptops = [];
  
    // Laptops von der API laden
    async function fetchLaptops() {
        // Ruft die Liste der Laptops von der API ab und initialisiert die Preise
        try {
            const response = await fetch("http://localhost:5001/api/laptops");
            laptops = await response.json();
            laptops.forEach(laptop => {
                laptop.preis = Math.floor(Math.random() * (2000 - 500 + 1)) + 500;
            });
            filteredLaptops = [...laptops];
            renderLaptopList();
        } catch (error) {
            console.error("Fehler beim Abrufen der Laptops:", error);
        }
    }
  
    async function fetchLaptopDetails(id) {
        // Ruft die Details eines spezifischen Laptops von der API ab und zeigt sie an
        try {
            const response = await fetch(`http://localhost:5001/api/laptop/${id}`);
            selectedLaptop = await response.json();
    
            document.getElementById("detail-title").innerText = selectedLaptop.name;
            document.getElementById("detail-manufacturer").innerText = selectedLaptop.hersteller;
            document.getElementById("detail-modell").innerText = selectedLaptop.modell;
            document.getElementById("detail-specifications").innerText = selectedLaptop.spezifikationen;
            document.getElementById("detail-price").innerText = `Preis: ${selectedLaptop.preis}€`;
    
            document.getElementById("add-to-cart").onclick = () => addToCart(selectedLaptop);
            document.getElementById("laptop-detail").style.display = "flex";
        } catch (error) {
            console.error("Fehler beim Abrufen der Laptop-Details:", error);
        }
    }
  
    function showDetail(id) {
        // Zeigt die Detailansicht eines Laptops basierend auf der ID
        fetchLaptopDetails(id);
    }
  
    function renderLaptopList() {
        // Rendert die Liste der Laptops basierend auf den gefilterten Daten
        const listContainer = document.getElementById("laptop-list");
        if (!listContainer) return;
        listContainer.innerHTML = "";
        filteredLaptops.forEach(laptop => {
            const laptopDiv = document.createElement("div");
            laptopDiv.className = "laptop-item";
            laptopDiv.innerHTML = `
                <h3>${laptop.name}</h3>
                <p>Hersteller: ${laptop.hersteller}</p>
                <p>Model: ${laptop.modell}</p>
                <p>Spezifikationen: ${laptop.spezifikationen}</p>
                <p>Preis: ${laptop.preis}€</p>
                <button>Details</button>
            `;
            laptopDiv.querySelector("button").addEventListener("click", () => showDetail(laptop.produkt_id));
            listContainer.appendChild(laptopDiv);
        });
    }
  
    function closeDetail() {
        // Schließt die Detailansicht
        document.getElementById("laptop-detail").style.display = "none";
    }
  
    function addToCart(laptop) {
        // Fügt einen Laptop zum Warenkorb hinzu und aktualisiert die Ansicht
        if (laptop) {
            cart.push(laptop);
            renderCart();
            closeDetail();
        }
    }
  
    function renderCart() {
        // Rendert die Warenkorb-Ansicht und berechnet den Gesamtpreis
        const cartContainer = document.getElementById("cart-items");
        cartContainer.innerHTML = "";
        let total = 0;
        cart.forEach((item, index) => {
            total += item.preis;
            const itemDiv = document.createElement("div");
            itemDiv.className = "cart-item";
            itemDiv.innerHTML = `
                <span>${item.name} - ${item.preis}€</span>
                <button onclick="removeFromCart(${index})">Entfernen</button>
            `;
            cartContainer.appendChild(itemDiv);
        });
        document.getElementById("total-price").innerText = `Gesamtpreis: ${total}€`;
    }
  
    function removeFromCart(index) {
        // Entfernt einen Laptop aus dem Warenkorb basierend auf dem Index
        cart.splice(index, 1);
        renderCart();
    }
  
    async function purchaseOrder() {
        // Sendet die Bestellung an die API und zeigt die Bestellbestätigung an
        if (cart.length === 0) {
            alert("Ihr Warenkorb ist leer!");
            return;
        }
    
        try {
            const response = await fetch("http://localhost:5001/api/order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cart }),
            });
    
            const result = await response.json();
            document.getElementById("order-info").innerHTML = `
                <p>Bestellnummer: ${result.orderId}</p>
                <p>Gesamtbetrag: ${cart.reduce((sum, item) => sum + item.preis, 0)}€</p>
            `;
            document.getElementById("order-confirmation").style.display = "flex";
    
            cart = [];
            renderCart();
        } catch (error) {
            console.error("Fehler bei der Bestellung:", error);
        }
    }
  
    function closeConfirmation() {
        // Schließt die Bestellbestätigungsansicht
        document.getElementById("order-confirmation").style.display = "none";
    }
  
    function handleSearch() {
        // Filtert die Laptops basierend auf dem Suchbegriff
        const searchInput = document.getElementById("search-input");
        const searchTerm = searchInput.value.trim().toLowerCase();
    
        if (!searchTerm) {
            filteredLaptops = [...laptops];
        } else {
            filteredLaptops = laptops.filter(laptop =>
                laptop.name.toLowerCase().includes(searchTerm) ||
                laptop.hersteller.toLowerCase().includes(searchTerm) ||
                laptop.modell.toLowerCase().includes(searchTerm) ||
                laptop.spezifikationen.toLowerCase().includes(searchTerm)
            );
        }
    
        applySort();
        renderLaptopList();
    
        if (filteredLaptops.length === 0) {
            document.getElementById("laptop-list").innerHTML =
                "<p>Keine Ergebnisse gefunden.</p>";
        }
    }
  
    function handleSort() {
        // Sortiert die Laptops basierend auf der ausgewählten Sortieroption
        applySort();
        renderLaptopList();
    }
  
    function applySort() {
        // Wendet die Sortierlogik auf die gefilterten Laptops an
        const sortValue = document.getElementById("sort-select").value;
        if (sortValue === "price-asc") {
            filteredLaptops.sort((a, b) => a.preis - b.preis);
        } else if (sortValue === "price-desc") {
            filteredLaptops.sort((a, b) => b.preis - a.preis);
        } else if (sortValue === "name-asc") {
            filteredLaptops.sort((a, b) => a.name.localeCompare(b.name));
        } else if (sortValue === "name-desc") {
            filteredLaptops.sort((a, b) => b.name.localeCompare(a.name));
        }
    }
  
    function handleRouting() {
        // Handhabt die Navigation zwischen den Hauptabschnitten (Laptops, Warenkorb)
        const hash = window.location.hash;
        const sections = ["laptops", "cart"];
        sections.forEach(section => {
            document.getElementById(section).style.display = (hash === `#${section}`) ? "block" : "none";
        });
        if (!hash) {
            document.getElementById("laptops").style.display = "block";
        }
    }
  
    // Event Listener
    // Initialisiert die Event-Listener für Suche, Sortierung und Routing
    document.getElementById("search-input").addEventListener("input", handleSearch);
    document.getElementById("sort-select").addEventListener("change", handleSort);
    window.addEventListener("hashchange", handleRouting);
  
    // Initial
    // Lädt die Laptops und setzt die Standardansicht
    fetchLaptops();
    handleRouting();
});
