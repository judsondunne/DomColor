const express = require('express');
const axios = require('axios');
const { Vibrant } = require('node-vibrant/node');

const app = express();

// Middleware to parse JSON bodies
app.use(express.json());

app.post('/dominant-color', async (req, res) => {
  const { photoUrl } = req.body;
  
  if (!photoUrl) {
    return res.status(400).json({ error: "Please provide a photoUrl in the request body" });
  }

  try {
    // Fetch the image data using axios
    const response = await axios.get(photoUrl, { responseType: 'arraybuffer' });
    const imageBuffer = Buffer.from(response.data, 'binary');
    
    // Pass the buffer to Vibrant to get the palette
    const palette = await Vibrant.from(imageBuffer).getPalette();
    
    // Use the Vibrant swatch, checking if getHex is available.
    const vibrantSwatch = palette.Vibrant;
    const dominantColor =
      vibrantSwatch && typeof vibrantSwatch.getHex === 'function'
        ? vibrantSwatch.getHex()
        : vibrantSwatch && vibrantSwatch.hex
        ? vibrantSwatch.hex
        : null;
    
    if (!dominantColor) {
      return res.status(500).json({ error: "Could not extract a dominant color from the image." });
    }
    
    return res.json({ dominantColor });
  } catch (error) {
    console.error("Error processing image:", error);
    return res.status(500).json({ error: "Error processing the image." });
  }
});

const PORT = process.env.PORT || 3048;
app.listen(PORT, () => {
  console.log(`Express server running on port ${PORT}`);
});
