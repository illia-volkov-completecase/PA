const poster = (id, url, fields, cb = null) => {
    $(id).jsGrid({
        width: "100%",
        height: "20%",

        autoload: false,
        pageLoading: false,

        inserting: true,
        editing: false,
        fields: [
            ...(Object.entries(fields).map(pair => {return {
                name: pair[0],
                type: pair[1],
                align: "center"
            };})),
            {type: "control", deleteButton: false, editButton: false}
        ],
        controller: {
            insertItem: (data) => {
                if (cb) {
                    return cb(data);
                }

                return new Promise(resolve => {
                    post_data(url, data);
                    return resolve(data);
                })
            }
        }
    });
};

const post_data = (url, data = {}, method = 'POST') => {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    }).then(r => {
        if (!r.ok) {
            return r.json().then(data => alert(JSON.stringify(data)));
        };
        return r.json();
    });
};
