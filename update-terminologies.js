import fs from "fs"
import { jsonld2rdf } from "jsonld2rdf"

const url = "https://bartoc.org/api/voc?partOf=http%3A%2F%2Fbartoc.org%2Fen%2Fnode%2F18961&limit=500"
var terminologies = await fetch(url).then(res => res.json())
var namespaces = {}

const data = Object.fromEntries(fs.readFileSync('terminology-data.csv').toString().split("\n").slice(1,-1)
  .map(line => {
    const [uri, download, format] = line.split(",")
    return [uri, { download, format: `http://format.gbv.de/${format}` }]
  }))

var datacount=0
terminologies = terminologies.map(terminology => {
  const { uri } = terminology
  for (let field of ["distributions","creator","contributor","created","modified","concepts","topConcepts"]) {
    delete terminology[field]
  }
  if (data[uri]) {
    datacount++
    const { donwload, format } = data[uri]
    terminology.distributions = [data[uri]]
  }
  if (terminology.namespace) {
    namespaces[uri] = terminology.namespace
  }
  return terminology
})

const write = (file, content) => {
  console.log(file)
  fs.writeFileSync(file, content)
}

console.log(`${terminologies.length} terminologies, ${datacount} with download URL, ${Object.keys(namespaces).length} with namespace`)

write("stage/terminology/terminologies.json", JSON.stringify(terminologies, null, 2))
write("stage/terminology/namespaces.json", JSON.stringify(namespaces, null, 2))

const context = JSON.parse(fs.readFileSync("jskos-context.json"))
const prefixes = JSON.parse(fs.readFileSync("prefixes.json"))
const ttl = await jsonld2rdf(terminologies, { context, prefixes })
write("stage/terminology/terminologies.ttl", ttl)
