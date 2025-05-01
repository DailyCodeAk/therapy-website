// Tab switching functionality
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const tabId = e.currentTarget.getAttribute('data-tab');
        
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Show selected tab content
        document.getElementById(`${tabId}-tab`).classList.add('active');
        
        // Update page title
        document.getElementById('page-title').textContent = e.currentTarget.querySelector('.sidebar-full').textContent;
    });
});

// Sidebar toggle functionality
document.getElementById('toggle-sidebar').addEventListener('click', () => {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');
});

// User dropdown menu
const userMenuButton = document.getElementById('user-menu-button');
const userDropdown = document.getElementById('user-dropdown');

userMenuButton.addEventListener('click', () => {
    userDropdown.classList.toggle('hidden');
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!userMenuButton.contains(e.target) && !userDropdown.contains(e.target)) {
        userDropdown.classList.add('hidden');
    }
});

// Logout functionality
document.getElementById('logout-btn').addEventListener('click', (e) => {
    e.preventDefault();
    window.location.href = '/api/logout';
});

// Calendar navigation
const calendarPrevBtn = document.querySelector('#calendar-tab .fa-chevron-left').parentElement;
const calendarNextBtn = document.querySelector('#calendar-tab .fa-chevron-right').parentElement;

calendarPrevBtn.addEventListener('click', () => {
    // Add calendar navigation logic here
    console.log('Previous month clicked');
});

calendarNextBtn.addEventListener('click', () => {
    // Add calendar navigation logic here
    console.log('Next month clicked');
});

// Chat functionality
const chatInput = document.querySelector('#chat-tab input[type="text"]');
const chatSendBtn = document.querySelector('#chat-tab .fa-paper-plane').parentElement;

chatSendBtn.addEventListener('click', () => {
    const message = chatInput.value.trim();
    if (message) {
        // Add message to chat
        const chatContainer = document.querySelector('#chat-tab .overflow-y-auto');
        const newMessage = document.createElement('div');
        newMessage.className = 'flex items-start justify-end';
        newMessage.innerHTML = `
            <div class="bg-indigo-100 rounded-lg p-3 max-w-xs">
                <p class="text-sm">${message}</p>
                <p class="text-xs text-gray-500 mt-1">${new Date().toLocaleString()}</p>
            </div>
            <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 ml-2">
                <i class="fas fa-user"></i>
            </div>
        `;
        chatContainer.appendChild(newMessage);
        chatInput.value = '';
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});

// Profile form submission
const profileForm = document.querySelector('#profile-tab form');
if (profileForm) {
    profileForm.addEventListener('submit', (e) => {
        e.preventDefault();
        // Add profile update logic here
        alert('Profile updated successfully!');
    });
}

// Book session functionality
document.querySelectorAll('#therapists-tab .bg-indigo-600').forEach(button => {
    button.addEventListener('click', () => {
        // Add booking logic here
        alert('Session booking initiated!');
    });
});

// View session notes
document.querySelectorAll('#sessions-tab .bg-indigo-600').forEach(button => {
    button.addEventListener('click', () => {
        // Add view notes logic here
        alert('Session notes opened!');
    });
});

// Download session summary
document.querySelectorAll('#sessions-tab .bg-gray-100').forEach(button => {
    button.addEventListener('click', () => {
        // Add download logic here
        alert('Session summary downloaded!');
    });
});

// Support contact buttons
document.querySelectorAll('#support-tab .bg-indigo-600').forEach(button => {
    button.addEventListener('click', () => {
        // Add support contact logic here
        alert('Support ticket created!');
    });
});

// Emergency contact button
document.querySelector('#support-tab .bg-red-600').addEventListener('click', () => {
    if (confirm('Are you sure you want to contact emergency services?')) {
        // Add emergency contact logic here
        alert('Emergency services contacted!');
    }
});

// Initialize tooltips
document.querySelectorAll('[data-tooltip]').forEach(element => {
    element.addEventListener('mouseenter', () => {
        const tooltip = document.createElement('div');
        tooltip.className = 'absolute bg-gray-900 text-white px-2 py-1 rounded text-xs';
        tooltip.textContent = element.getAttribute('data-tooltip');
        element.appendChild(tooltip);
    });
    
    element.addEventListener('mouseleave', () => {
        const tooltip = element.querySelector('.absolute');
        if (tooltip) {
            tooltip.remove();
        }
    });
}); 