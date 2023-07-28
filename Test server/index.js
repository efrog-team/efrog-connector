const express = require('express');
const app = express();
app.use(express.json());

app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

const { MongoClient } = require("mongodb");
const client = new MongoClient('mongodb+srv://admin:RwaLv4WhzkKNO1dj@cluster0.umpxarg.mongodb.net/?retryWrites=true&w=majority')

app.get('/', (req, res) => {
    res.send('Server works');
});

app.get('/get-data', async (req, res) => {
    await client.connect();
    let data = JSON.stringify(await client.db('test').collection('test').find().toArray()).toString();
    await client.close();
    res.send(data);
});

app.post('/post-data', express.urlencoded({ extended: false }), async (req, res) => {
    await client.connect();
    await client.db('test').collection('test').insertOne({
        data: req.body.data
    });
    await client.close();
    res.send('Data added');
});

app.listen(process.env.PORT || 3000);

module.exports = app;