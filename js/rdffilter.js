import { filterPipeline, namespaceFilter } from "rdffilter"

const relativeIRI = iri => iri.startsWith("file://") || !/^(?:[a-z+]+:)/i.test(iri)
const isRelative = node => node.termType === "NamedNode" && relativeIRI(node.id)
const disallowRelativeIRIs = ({subject, object}) => !(isRelative(subject) || isRelative(object))

// TODO: load from config file
const nsReplace = namespaceFilter({
  namespaces: {
    "http://www.ics.forth.gr/isl/CRMsci/": "http://www.cidoc-crm.org/extensions/crmsci/",
    "http://www.ics.forth.gr/isl/CRMinf/": "http://www.cidoc-crm.org/extensions/crminf/",
    "http://www.ics.forth.gr/isl/CRMdig/": "http://www.cidoc-crm.org/extensions/crmdig/",
    "http://purl.org/dc/terms/": "http://purl.org/dc/elements/1.1/",
    "http://cidoc-crm.org/current/": "http://www.cidoc-crm.org/cidoc-crm/",
    "http://erlangen-crm.org/170309/": "http://www.cidoc-crm.org/cidoc-crm/",
  },
})

// Filter out triples about known vocabularies

import fs from "fs"
const stage = process.env.STAGE || 'stage'
const terminologyNamespaces = JSON.parse(fs.readFileSync(`${stage}/terminology/namespaces.json`))

const namespaces = {}
for (let uri in terminologyNamespaces) {
  const namespace = terminologyNamespaces[uri] 
  if (namespace != process.env.RDFFILTER_ALLOW_NAMESPACE) {
    namespaces[namespace] = false
  }
}

const disallowedSubjects = namespaceFilter({ range: ["subject"], namespaces })

export default filterPipeline([
  disallowRelativeIRIs,
  // replace known legacy namespaces
  nsReplace,
  // disallow as subject
  disallowedSubjects,
])
