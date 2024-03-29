// function for flattening json
const flattenJSON = (obj = {}, res = {}, extraKey = "") => {
  for (const key in obj) {
    if (obj[key]===null) res[extraKey + key]="null"
    else if (typeof obj[key] !== "object") {
      res[extraKey + key] = obj[key];
    } else {
      res[extraKey + key] =
        obj[key].constructor === Object
          ? { type: "dict", size: Object.keys(obj[key]).length }
          : { type: "list", size: obj[key].length };
      //`{${Object.keys(obj[key]).length}}↴` : `[${obj[key].length}]↴`;
      flattenJSON(obj[key], res, `${extraKey}${key}.`);
    }
  }
  return res;
};

// MAYBE USEFUL!! read an object value given a flat key
// const readFlat = (obj = {}, flatKey) => {
//   const keyList = flatKey.split(".");
//   var loc = obj;
//   for (const key in keyList) {
//     loc = loc[key];
//   }
//   return loc;
// };

//write an object value given a flat key
const writeFlat = (obj = {}, flatKey, value) => {
  const keyList = flatKey.split(".");
  var loc = obj;
  for (const [i, key] of keyList.entries()) {
    //if the last key, set the value
    if (i === keyList.length - 1) loc[key] = value;
    //otherwise keep traversing the object
    else loc = loc[key];
  }
  return loc;
};

// function for unflattening json
const unFlattenJSON = (flattenedJSON) => {
  const obj = {};
  for (const key in flattenedJSON) {
    var curr = flattenedJSON[key];

    //in the case the key is for a list or dictionary structure
    if (curr.constructor === Object) {
      curr["type"] === "list" ? (curr = []) : (curr = {});
    }

    writeFlat(obj, key, curr);
  }
  return obj;
};

export { flattenJSON, unFlattenJSON };
