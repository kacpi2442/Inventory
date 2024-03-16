function unhide(id) {
    document.getElementById(id).style.display = 'block';
}
function hide(id) {
    document.getElementById(id).style.display = 'none';
}

document.getElementById('delete-selected').addEventListener('click', (ev) => unhide('delete-dialog'));
document.getElementById('change-ownership').addEventListener('click', (ev) => unhide('change-ownership-dialog'));
document.getElementById('change-parent').addEventListener('click', (ev) => unhide('change-parent-dialog'));

document.getElementById('delete-no').addEventListener('click', (ev) => hide('delete-dialog'));
document.getElementById('change-ownership-no').addEventListener('click', (ev) => hide('change-ownership-dialog'));
document.getElementById('change-parent-no').addEventListener('click', (ev) => hide('change-parent-dialog'));

function getSelectedCheckboxIds() {
    if (document.getElementById('selectAll').checked) {
        return -1;
    }
    var selectedProperties = [];
    var checkboxes = document.querySelectorAll('input[type="checkbox"]:checked.select');
    for (var i = 0; i < checkboxes.length; i++) {
        selectedProperties.push(checkboxes[i].id);
    }
    return selectedProperties;
}

document.getElementById('delete-yes').addEventListener('click', (ev) => {
    // Get the selected properties
    var selectedProperties = getSelectedCheckboxIds();
    var search = document.getElementById('search').value;
    var reqBody = JSON.stringify({selected: selectedProperties, search: search});
    console.log(reqBody);


    // Send the selected properties to the server
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/delete_multiple', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(reqBody);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log(xhr.responseText);
            hide('delete-dialog');
            window.location.reload();
        }else if (xhr.readyState == 4 && xhr.status != 200) {
            console.log(xhr.responseText);
            hide('delete-dialog');
            document.getElementById('table-error-message').innerHTML = xhr.responseText;
        }
    };
    }
);

document.getElementById('change-ownership-yes').addEventListener('click', (ev) => {
    var owner = document.getElementById('change-ownership-dialog-ownerships').value;
    var selectedProperties = getSelectedCheckboxIds();
    var search = document.getElementById('search').value;
    var reqBody = JSON.stringify({owner_id: owner, selected: selectedProperties, search: search});
    console.log(reqBody);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/change_ownership', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(reqBody);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log(xhr.responseText);
            hide('change-ownership-dialog');
            window.location.reload();
        }else if (xhr.readyState == 4 && xhr.status != 200) {
            console.log(xhr.responseText);
            hide('change-ownership-dialog');
            document.getElementById('table-error-message').innerHTML = xhr.responseText;
        }
    };
    }
);

document.getElementById('change-parent-yes').addEventListener('click', (ev) => {
    var parent = document.getElementById('change-parent-dialog-parent').value;
    var selectedIds = getSelectedCheckboxIds();
    var search = document.getElementById('search').value;
    var reqBody = JSON.stringify({parent_id: parent, selected: selectedIds, search: search});
    console.log(reqBody);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/change_parent', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(reqBody);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log(xhr.responseText);
            hide('change-parent-dialog');
            window.location.reload();
        }else if (xhr.readyState == 4 && xhr.status != 200) {
            console.log(xhr.responseText);
            hide('change-parent-dialog');
            document.getElementById('table-error-message').innerHTML = xhr.responseText;
        }
    };
    }
);

document.getElementById('selectAll').addEventListener('change', (ev) => {
    var checkboxes = document.querySelectorAll('input[type="checkbox"].select');
    for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = ev.target.checked;
    }
    if (ev.target.checked) {
        document.getElementById('table-modify-buttons').style.display = 'flex';
    } else {
        hide('table-modify-buttons');
    }
});

document.querySelectorAll('input[type="checkbox"].select').forEach((checkbox) => {
    checkbox.addEventListener('change', (ev) => {
        if (ev.target.checked) {
            document.getElementById('table-modify-buttons').style.display = 'flex';
        } else {
            document.getElementById('selectAll').checked = false;
            if (getSelectedCheckboxIds().length == 0) {
                hide('table-modify-buttons');
            }
        }
    });
}
);