// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// API базовый URL
const API_BASE = '/api';

// Состояние формы
let cities = [];
let objects = [];
let violationCategories = [];
let violations = [];

// Проверка авторизации при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    // Проверяем, авторизован ли пользователь
    if (tg.initData) {
        try {
            const response = await fetch(`${API_BASE}/users/check-access`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Init-Data': tg.initData
                },
                body: JSON.stringify({})
            });

            const result = await response.json();

            if (!result.success || !result.authorized) {
                // Пользователь не авторизован, показываем сообщение об ошибке
                showMessage('Доступ запрещен: Пользователь не зарегистрирован в системе', 'error');
                // Блокируем всю форму
                document.querySelectorAll('select, textarea, input, button').forEach(element => {
                    element.disabled = true;
                });
                // Также закрываем приложение через Telegram WebApp
                setTimeout(() => {
                    if (tg.close) {
                        tg.close();
                    }
                }, 3000); // Закрытие через 3 секунды после отображения ошибки
                return;
            }
        } catch (error) {
            console.error('Error checking user access:', error);
        }
    }

    loadCities();
    loadViolationCategories();
    setupFormHandlers();
});

// Загрузка городов
async function loadCities() {
    try {
        const response = await fetch(`${API_BASE}/cities`);
        const result = await response.json();
        
        if (result.success) {
            cities = result.data;
            const citySelect = document.getElementById('city');
            citySelect.innerHTML = '<option value="">Выберите город</option>';
            // В форме city_id — это btxid города (для form_submissions)
            cities.filter(city => city.btxid != null).forEach(city => {
                const option = document.createElement('option');
                option.value = city.btxid;
                option.textContent = city.name;
                citySelect.appendChild(option);
            });
        } else {
            showMessage('Ошибка загрузки городов: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error loading cities:', error);
        showMessage('Ошибка загрузки городов', 'error');
    }
}

// Загрузка объектов по городу
async function loadObjects(cityId) {
    const objectSelect = document.getElementById('object');
    objectSelect.disabled = true;
    objectSelect.innerHTML = '<option value="">Загрузка...</option>';
    
    try {
        const response = await fetch(`${API_BASE}/objects?city_id=${cityId}`);
        const result = await response.json();
        
        if (result.success) {
            objects = result.data;
            objectSelect.innerHTML = '<option value="">Выберите объект</option>';
            
            if (objects.length === 0) {
                objectSelect.innerHTML = '<option value="">Нет объектов для выбранного города</option>';
            } else {
                objects.filter(obj => obj.btxid != null).forEach(obj => {
                    const option = document.createElement('option');
                    option.value = obj.btxid;
                    option.textContent = obj.name;
                    objectSelect.appendChild(option);
                });
                objectSelect.disabled = false;
            }
        } else {
            objectSelect.innerHTML = '<option value="">Ошибка загрузки объектов</option>';
            showMessage('Ошибка загрузки объектов: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error loading objects:', error);
        objectSelect.innerHTML = '<option value="">Ошибка загрузки объектов</option>';
        showMessage('Ошибка загрузки объектов', 'error');
    }
}

// Загрузка категорий нарушений
async function loadViolationCategories() {
    try {
        const response = await fetch(`${API_BASE}/violation-categories`);
        const result = await response.json();
        
        if (result.success) {
            violationCategories = result.data;
            const categorySelect = document.getElementById('violationCategory');
            categorySelect.innerHTML = '<option value="">Выберите категорию</option>';
            
            violationCategories.filter(cat => cat.btxid != null).forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.btxid;
                option.textContent = cat.name;
                categorySelect.appendChild(option);
            });
        } else {
            showMessage('Ошибка загрузки категорий: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error loading violation categories:', error);
        showMessage('Ошибка загрузки категорий', 'error');
    }
}

// Загрузка нарушений по категории
async function loadViolations(categoryId) {
    const violationSelect = document.getElementById('violation');
    violationSelect.disabled = true;
    violationSelect.innerHTML = '<option value="">Загрузка...</option>';
    
    try {
        const response = await fetch(`${API_BASE}/violations?category_id=${categoryId}`);
        const result = await response.json();
        
        if (result.success) {
            violations = result.data;
            violationSelect.innerHTML = '<option value="">Выберите нарушение</option>';
            
            if (violations.length === 0) {
                violationSelect.innerHTML = '<option value="">Нет нарушений для выбранной категории</option>';
            } else {
                violations.filter(viol => viol.btxid != null).forEach(viol => {
                    const option = document.createElement('option');
                    option.value = viol.btxid;
                    option.textContent = viol.name;
                    violationSelect.appendChild(option);
                });
                violationSelect.disabled = false;
            }
        } else {
            violationSelect.innerHTML = '<option value="">Ошибка загрузки нарушений</option>';
            showMessage('Ошибка загрузки нарушений: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error loading violations:', error);
        violationSelect.innerHTML = '<option value="">Ошибка загрузки нарушений</option>';
        showMessage('Ошибка загрузки нарушений', 'error');
    }
}

// Настройка обработчиков формы
function setupFormHandlers() {
    const form = document.getElementById('dataForm');
    const citySelect = document.getElementById('city');
    const categorySelect = document.getElementById('violationCategory');
    const fileInput = document.getElementById('file');
    
    // Обработчик изменения города
    citySelect.addEventListener('change', function() {
        const cityId = this.value;
        const objectSelect = document.getElementById('object');
        
        if (cityId) {
            loadObjects(cityId);
        } else {
            objectSelect.disabled = true;
            objectSelect.innerHTML = '<option value="">Сначала выберите город</option>';
        }
        
        // Очистка выбранного объекта
        objectSelect.value = '';
    });
    
    // Обработчик изменения категории нарушения
    categorySelect.addEventListener('change', function() {
        const categoryId = this.value;
        const violationSelect = document.getElementById('violation');
        
        if (categoryId) {
            loadViolations(categoryId);
        } else {
            violationSelect.disabled = true;
            violationSelect.innerHTML = '<option value="">Сначала выберите категорию</option>';
        }
        
        // Очистка выбранного нарушения
        violationSelect.value = '';
    });
    
    // Обработчик выбора файлов
    fileInput.addEventListener('change', function() {
        const files = Array.from(this.files || []);
        const errorElement = document.getElementById('file-error');
        errorElement.textContent = '';
        
        if (files.length > 5) {
            errorElement.textContent = 'Можно прикрепить не более 5 файлов';
            this.value = '';
            return;
        }
        
        const maxSize = 50 * 1024 * 1024;
        for (const file of files) {
            if (file.size > maxSize) {
                errorElement.textContent = `Файл "${file.name}" превышает 50 МБ`;
                this.value = '';
                return;
            }
        }
    });
    
    // Обработчик отправки формы
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        await submitForm();
    });
}

// Валидация формы
function validateForm() {
    let isValid = true;
    
    // Очистка предыдущих ошибок
    document.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
    });
    
    const cityId = document.getElementById('city').value;
    const objectId = document.getElementById('object').value;
    const categoryId = document.getElementById('violationCategory').value;
    const violationId = document.getElementById('violation').value;
    
    if (!cityId) {
        document.getElementById('city-error').textContent = 'Выберите город';
        isValid = false;
    }
    
    if (!objectId) {
        document.getElementById('object-error').textContent = 'Выберите объект';
        isValid = false;
    }
    
    if (!categoryId) {
        document.getElementById('violationCategory-error').textContent = 'Выберите категорию нарушения';
        isValid = false;
    }
    
    if (!violationId) {
        document.getElementById('violation-error').textContent = 'Выберите нарушение';
        isValid = false;
    }
    
    return isValid;
}

// Отправка формы
async function submitForm() {
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const submitLoader = document.getElementById('submitLoader');
    const form = document.getElementById('dataForm');
    
    // Блокировка кнопки
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitLoader.style.display = 'inline-block';
    
    try {
        const formData = new FormData(form);
        
        // Добавляем Telegram initData если доступен
        if (tg.initData) {
            // Отправляем initData через заголовок
            const response = await fetch(`${API_BASE}/submit`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Telegram-Init-Data': tg.initData
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                showMessage('Данные успешно отправлены!', 'success');
                form.reset();
                
                // Сброс зависимых полей
                document.getElementById('object').disabled = true;
                document.getElementById('object').innerHTML = '<option value="">Сначала выберите город</option>';
                document.getElementById('violation').disabled = true;
                document.getElementById('violation').innerHTML = '<option value="">Сначала выберите категорию</option>';
                
                // Вибрация при успехе (если поддерживается)
                if (tg.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            } else {
                showMessage('Ошибка: ' + result.error, 'error');
                if (tg.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('error');
                }
            }
        } else {
            // Отправка без Telegram данных (для тестирования)
            const response = await fetch(`${API_BASE}/submit`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                showMessage('Данные успешно отправлены!', 'success');
                form.reset();
                
                document.getElementById('object').disabled = true;
                document.getElementById('object').innerHTML = '<option value="">Сначала выберите город</option>';
                document.getElementById('violation').disabled = true;
                document.getElementById('violation').innerHTML = '<option value="">Сначала выберите категорию</option>';
            } else {
                showMessage('Ошибка: ' + result.error, 'error');
            }
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        showMessage('Ошибка отправки данных: ' + error.message, 'error');
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    } finally {
        // Разблокировка кнопки
        submitBtn.disabled = false;
        submitText.style.display = 'inline';
        submitLoader.style.display = 'none';
    }
}

// Показать сообщение
function showMessage(text, type) {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    messageEl.style.display = 'block';
    
    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        messageEl.style.display = 'none';
    }, 5000);
    
    // Прокрутка к сообщению
    messageEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


