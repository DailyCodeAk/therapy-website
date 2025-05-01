// Function to fetch and update dashboard data
async function updateDashboardData() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        // Update next appointment
        if (data.nextAppointment) {
            const nextAppointmentDiv = document.querySelector('#dashboard-tab .bg-gray-50');
            nextAppointmentDiv.innerHTML = `
                <div class="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 mr-4">
                    <i class="fas fa-calendar-day"></i>
                </div>
                <div>
                    <p class="font-medium">${data.nextAppointment.therapistName}</p>
                    <p class="text-sm text-gray-500">${data.nextAppointment.dateTime}</p>
                </div>
            `;
        }
        
        // Update recent goals
        if (data.recentGoals && data.recentGoals.length > 0) {
            const goalsContainer = document.querySelector('#dashboard-tab .space-y-4');
            goalsContainer.innerHTML = data.recentGoals.map(goal => `
                <div class="mb-3">
                    <div class="flex items-center justify-between">
                        <p class="font-medium">${goal.title}</p>
                        <span class="text-xs bg-${goal.progress >= 75 ? 'green' : 'blue'}-100 text-${goal.progress >= 75 ? 'green' : 'blue'}-800 px-2 py-1 rounded">${goal.progress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div class="bg-${goal.progress >= 75 ? 'green' : 'blue'}-500 h-2 rounded-full" style="width: ${goal.progress}%"></div>
                    </div>
                </div>
            `).join('');
        }
        
        // Update billing summary
        if (data.billingSummary) {
            const billingContainer = document.querySelector('#dashboard-tab .space-y-4');
            billingContainer.innerHTML = `
                <div class="mb-3 pb-3 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <p class="font-medium">Last Payment</p>
                        <p class="font-medium text-gray-900">$${data.billingSummary.lastPayment.amount}</p>
                    </div>
                    <p class="text-sm text-gray-500">${data.billingSummary.lastPayment.date}</p>
                </div>
                <div>
                    <div class="flex items-center justify-between">
                        <p class="font-medium">Next Payment</p>
                        <p class="font-medium text-gray-900">$${data.billingSummary.nextPayment.amount}</p>
                    </div>
                    <p class="text-sm text-gray-500">${data.billingSummary.nextPayment.date}</p>
                </div>
            `;
        }
        
        // Update recent activity
        if (data.recentActivity && data.recentActivity.length > 0) {
            const activityContainer = document.querySelector('#dashboard-tab .space-y-4');
            activityContainer.innerHTML = data.recentActivity.map(activity => `
                <div class="flex items-start">
                    <div class="w-10 h-10 rounded-full bg-${activity.type === 'appointment' ? 'blue' : 'green'}-100 flex items-center justify-center text-${activity.type === 'appointment' ? 'blue' : 'green'}-600 mr-4">
                        <i class="fas fa-${activity.type === 'appointment' ? 'calendar-check' : 'check-circle'}"></i>
                    </div>
                    <div>
                        <p class="font-medium">${activity.title}</p>
                        <p class="text-sm text-gray-500">${activity.description}</p>
                        <p class="text-xs text-gray-400">${activity.date}</p>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error updating dashboard data:', error);
    }
}

// Function to fetch and update calendar events
async function updateCalendarEvents() {
    try {
        const response = await fetch('/api/calendar/events');
        const data = await response.json();
        
        // Update calendar events
        const calendarDays = document.querySelectorAll('.calendar-day');
        calendarDays.forEach(day => {
            const date = day.querySelector('.text-right').textContent;
            const events = data.events.filter(event => event.date === date);
            
            if (events.length > 0) {
                const eventIndicator = document.createElement('div');
                eventIndicator.className = 'mt-1 text-xs text-indigo-600';
                eventIndicator.textContent = `${events.length} event${events.length > 1 ? 's' : ''}`;
                day.appendChild(eventIndicator);
            }
        });
    } catch (error) {
        console.error('Error updating calendar events:', error);
    }
}

// Function to fetch and update chat messages
async function updateChatMessages() {
    try {
        const response = await fetch('/api/chat/messages');
        const data = await response.json();
        
        // Update chat messages
        const chatContainer = document.querySelector('#chat-tab .space-y-4');
        chatContainer.innerHTML = data.messages.map(message => `
            <div class="flex items-start ${message.sender === 'user' ? 'justify-end' : ''}">
                ${message.sender === 'therapist' ? `
                    <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 mr-2">
                        <i class="fas fa-user-md"></i>
                    </div>
                ` : ''}
                <div class="bg-${message.sender === 'user' ? 'indigo' : 'gray'}-100 rounded-lg p-3 max-w-xs">
                    <p class="text-sm">${message.content}</p>
                    <p class="text-xs text-gray-500 mt-1">${message.timestamp}</p>
                </div>
                ${message.sender === 'user' ? `
                    <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 ml-2">
                        <i class="fas fa-user"></i>
                    </div>
                ` : ''}
            </div>
        `).join('');
        
        // Scroll to bottom of chat
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (error) {
        console.error('Error updating chat messages:', error);
    }
}

// Function to fetch and update session notes
async function updateSessionNotes() {
    try {
        const response = await fetch('/api/sessions/notes');
        const data = await response.json();
        
        // Update session notes
        const sessionsContainer = document.querySelector('#sessions-tab .space-y-4');
        sessionsContainer.innerHTML = data.sessions.map(session => `
            <div class="border rounded-lg p-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="text-lg font-medium">Session with ${session.therapistName}</h3>
                        <p class="text-sm text-gray-500">${session.date} - ${session.time}</p>
                    </div>
                    <span class="bg-${session.status === 'completed' ? 'green' : 'yellow'}-100 text-${session.status === 'completed' ? 'green' : 'yellow'}-800 px-2 py-1 rounded text-sm">${session.status}</span>
                </div>
                <p class="mt-2 text-gray-600">${session.notes}</p>
                <div class="mt-4 flex space-x-2">
                    <button class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">View Notes</button>
                    <button class="bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200">Download Summary</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error updating session notes:', error);
    }
}

// Function to fetch and update billing information
async function updateBillingInfo() {
    try {
        const response = await fetch('/api/billing/info');
        const data = await response.json();
        
        // Update billing history
        const billingContainer = document.querySelector('#billing-tab .space-y-4');
        billingContainer.innerHTML = data.history.map(transaction => `
            <div class="border rounded-lg p-4">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="text-lg font-medium">${transaction.description}</h3>
                        <p class="text-sm text-gray-500">${transaction.date}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-lg font-medium">$${transaction.amount}</p>
                        <p class="text-sm text-${transaction.status === 'paid' ? 'green' : 'red'}-600">${transaction.status}</p>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Update payment method
        const paymentMethodContainer = document.querySelector('#billing-tab .border.rounded-lg.p-4');
        paymentMethodContainer.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <i class="fab fa-cc-${data.paymentMethod.type.toLowerCase()} text-2xl text-${data.paymentMethod.type === 'Visa' ? 'blue' : 'gray'}-600 mr-3"></i>
                    <div>
                        <p class="font-medium">${data.paymentMethod.type} ending in ${data.paymentMethod.last4}</p>
                        <p class="text-sm text-gray-500">Expires ${data.paymentMethod.expiry}</p>
                    </div>
                </div>
                <button class="text-indigo-600 hover:text-indigo-700">Edit</button>
            </div>
        `;
    } catch (error) {
        console.error('Error updating billing information:', error);
    }
}

// Set up periodic updates
document.addEventListener('DOMContentLoaded', () => {
    // Initial data load
    updateDashboardData();
    updateCalendarEvents();
    updateChatMessages();
    updateSessionNotes();
    updateBillingInfo();
    
    // Set up periodic updates
    setInterval(updateDashboardData, 30000); // Update every 30 seconds
    setInterval(updateCalendarEvents, 300000); // Update every 5 minutes
    setInterval(updateChatMessages, 10000); // Update every 10 seconds
    setInterval(updateSessionNotes, 300000); // Update every 5 minutes
    setInterval(updateBillingInfo, 300000); // Update every 5 minutes
}); 