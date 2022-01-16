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
