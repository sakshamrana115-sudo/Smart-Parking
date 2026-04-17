let slots = JSON.parse(localStorage.getItem('parking_slots')) || Array(12).fill(null);

function login() {
    const user = document.getElementById('username').value;
    if(user) {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        document.getElementById('welcome').innerText = `Welcome, ${user}`;
        renderGrid();
    }
}

function renderGrid() {
    const grid = document.getElementById('slot-grid');
    grid.innerHTML = '';
    slots.forEach((status, index) => {
        const div = document.createElement('div');
        div.className = `slot ${status ? 'booked' : 'free'}`;
        div.innerText = `Slot ${index + 1}`;
        div.onclick = () => openBooking(index);
        grid.appendChild(div);
    });
}

function openBooking(index) {
    if(slots[index]) {
        alert(`Booked by: ${slots[index].owner}\nVehicle: ${slots[index].vehicle}`);
        return;
    }
    document.getElementById('selected-slot').innerText = index + 1;
    document.getElementById('modal').classList.remove('hidden');
    window.currentSlot = index;
}

function confirmBooking() {
    const owner = document.getElementById('owner-name').value;
    const vehicle = document.getElementById('vehicle-no').value;
    
    if(owner && vehicle) {
        slots[window.currentSlot] = { owner, vehicle, time: new Date().toLocaleString() };
        localStorage.setItem('parking_slots', JSON.stringify(slots));
        
        // Generate QR
        document.getElementById('qrcode').innerHTML = "";
        new QRCode(document.getElementById("qrcode"), `Slot: ${window.currentSlot + 1}, Vehicle: ${vehicle}`);
        
        renderGrid();
        alert("Booking Successful!");
    }
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

function logout() {
    location.reload();
}