function packValuesToJson() {
    var item = {
        id: document.getElementById('id').value,
        name: document.getElementById('name').value,
        barcode: document.getElementById('barcode').value.split(','),
        parent: document.getElementById('parent').value,
        ownerships: [],
        properties: []
    };

    var ownerships = document.getElementById('ownerships').getElementsByClassName('owners');
    for (var i = 1; i <= ownerships.length; i++) {
        var ownership = {
            owner: document.getElementById('owner-' + i).value,
            own: document.getElementById('owner-value-' + i).value
        };
        item.ownerships.push(ownership);
    }

    var properties = document.getElementById('properties').getElementsByClassName('property');
    for (var i = 1; i <= properties.length; i++) {
        var property = {
            property: document.getElementById('property-' + i).value,
            value: document.getElementById('property-value-' + i).value
        };
        item.properties.push(property);
    }

    return JSON.stringify(item);
}

document.getElementById('form-edit-submit').addEventListener('click', function(e) {
    e.preventDefault();
    var json = packValuesToJson();
    console.log(json);
    // Send the JSON to /update endpoint
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/update', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(json);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log(xhr.responseText);
            document.getElementById('error-message').innerHTML = xhr.responseText;
            // window.location.href = '/list';
        }else if (xhr.readyState == 4 && xhr.status != 200) {
            console.log(xhr.responseText);
            document.getElementById('error-message').innerHTML = xhr.responseText;
        }
    };
});


// Function to remove a property
function removeProperty(event, id) {
    event.preventDefault();
    var propertyElement = event.target.parentNode;
    propertyElement.parentNode.removeChild(propertyElement);

    // Add the add button back to the last property
    var newProperty = document.createElement('button');
    newProperty.innerHTML = '+';
    newProperty.className = 'add_property';
    newProperty.addEventListener('click', ev => addProperty(ev, id));

    propertyElement = document.getElementById(id).lastElementChild;
    if (propertyElement.getElementsByClassName('add_property').length == 0)
        if (propertyElement)
            propertyElement.appendChild(newProperty);
        else
            document.getElementById(id).appendChild(newProperty);
}

// Function to add a new property
function addProperty(event, id) {
    event.preventDefault();

    // Remove the first add button
    var addButtons = document.querySelectorAll('div#'+id+' .add_property');
    // addButtons[0].style.display = 'none';
    if (addButtons.length > 0) addButtons[0].parentNode.removeChild(addButtons[0]);

    var propertiesContainer = document.getElementById(id);
    var newIndex = propertiesContainer.children.length + 1;

    var newProperty = document.createElement('div');
    
    var className = id == 'properties' ? 'property' : 'owners';
    var selectId = id == 'properties' ? 'property' : 'owner';
    newProperty.innerHTML = `
        <select id="${selectId}-${newIndex}" name="${className}" class="${className}" required>
        </select>
        <input type="text" id="${selectId}-value-${newIndex}" name="value" required>
        <button class="remove_property" value="${newIndex}">-</button>
        <button class="add_property">+</button>
    `;
    // newProperty.getElementsByTagName('select')[0].innerHTML = document.getElementById('property-1').innerHTML;
    newProperty.getElementsByTagName('select')[0].innerHTML = document.getElementById(id+'-sample').innerHTML;
    
    propertiesContainer.appendChild(newProperty);

    // Add event listeners to the new buttons
    newProperty.querySelector('.remove_property').addEventListener('click', (ev) => removeProperty(ev, id));
    newProperty.querySelector('.add_property').addEventListener('click', (ev) => addProperty(ev, id));
    newProperty.querySelector('select').addEventListener('change', (ev) => newPropertyListener(ev));

}

function existingButtons(id) {
    var removeButtons = document.querySelectorAll('div#'+id+' .remove_property');
    for (var i = 0; i < removeButtons.length; i++) {
        removeButtons[i].addEventListener('click', (ev) => removeProperty(ev, id));
    }

    var addButtons = document.querySelectorAll('div#'+id+' .add_property');
    for (var i = 0; i < addButtons.length; i++) {
        addButtons[i].addEventListener('click',(ev) => addProperty(ev, id));
    }

    console.log(id)
    if (document.getElementById(id).children.length == 0) {
        console.log(document.getElementById(id))
        addProperty({preventDefault: () => {}}, id);
    }
}

function newPropertyListener(event) {
    if (event.target.value == 'new') {
        newInput = document.createElement('input');
        newInput.type = 'text';
        newInput.id = event.target.id;
        newInput.name = event.target.name;
        newInput.className = event.target.className;
        newInput.required = true;
        event.target.replaceWith(newInput);

    }
}

function addNewPropertyListeners(name) {
    var propSelects = document.getElementsByClassName(name)
    for (var i = 0; i < propSelects.length; i++) {
        propSelects[i].addEventListener('change', (ev) => newPropertyListener(ev));
    }
}

existingButtons('properties');
existingButtons('ownerships');

addNewPropertyListeners('property');
addNewPropertyListeners('owners')