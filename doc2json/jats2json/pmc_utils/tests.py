
funding_tags_and_parsed_dicts = [
    # <funding-group> is typically the top-level tag
    #
    # within, we see <funding-source> and <funding-statement> as containing the main information we want
    #
    # here, we see <funding-source> with an 'id' attribute.  we can ignore these.
    ("""<funding-group>
            <award-group>
                <funding-source id=\"CS200\">Wellcome Trust</funding-source>
            </award-group>
        </funding-group>""", None),
    # sometimes, there are also <award-id> tags, but we can ignore these.  they're funding-group specific.
    ("""<funding-group>
            <award-group>
                <funding-source id=\"sp1\">US Department of Energy's Office of Science, Biological and Environmental Research Program</funding-source>
                <award-id rid=\"sp1\">DE-AC02-05CH11231</award-id>
                <award-id rid=\"sp1\">DE-AC52-07NA27344</award-id>
                <award-id rid=\"sp1\">DE-AC02-06NA25396</award-id>
                <award-id rid=\"sp1\">DE-AC05-00OR22725</award-id>
            </award-group>
            <award-group>
                <funding-source id=\"sp2\">German Research Foundation</funding-source>
                <award-id rid=\"sp2\">INST 599/1-2</award-id>
            </award-group>
        </funding-group>""", None),

    # <funding-statement> is a less structured alternative to <funding-source>
    ("""<funding-group>
            <funding-statement>No sources of funding were used to assist in the preparation of this study.</funding-statement>
        </funding-group>""", None),

    # Rarely, there is nesting!  ignore parents.
    ("""<funding-group>
            <funding-statement>
                <funding-source>This work was supported by the Swedish Association for Sexuality Education (RFSU).</funding-source>
            </funding-statement>
        </funding-group>""", None),


    # Sometimes both can occur, sort of duplicating the same information.
    # For example "Cornell" is mentioned as both a <funding-source> and a <funding-statement>
    ("""<funding-group>
            <award-group>
                <funding-source>
                    <named-content content-type=\"funder-name\">Cornell University Institute for the Social Sciences</named-content>
                </funding-source>
            </award-group>
            <funding-statement>The research was supported by a grant from the Cornell University Institute for the Social Sciences.</funding-statement>
        </funding-group>""", None),

    # many <funding-source>
    ("""<funding-group>
            <award-group id=\"sp1\">
                <funding-source>Brien Holden Vision Institute</funding-source>
            </award-group>
            <award-group id=\"sp2\">
                <funding-source>Australian Federal Government</funding-source>
            </award-group>
            <award-group id=\"sp3\">
                <funding-source>International Postgraduate Research Scholarship (Cathleen Fedtke)</funding-source>
            </award-group>
            <award-group id=\"sp4\">
                <funding-source>University of New South Wales, Australia</funding-source>
            </award-group>
            <award-group id=\"sp5\">
                <funding-source>National Institutes of Health</funding-source>
                <award-id>P30EY14801</award-id>
            </award-group>
            <award-group id=\"sp6\">
                <funding-source>Florida Lions Eye Bank</funding-source>
            </award-group>
            <award-group id=\"sp7\">
                <funding-source>Bascom Palmer Eye Institute</funding-source>
            </award-group>
        </funding-group>""", None),

    # institutions can optionally occur within <funding-source>
    # 'institution-id-type' is common, but also optional
    # regardless of the institution ID type, it looks like the ID is always a DOI (or URL to a DOI)
    ("""<funding-group>
            <award-group>
                <funding-source>
                    <institution-wrap>
                        <institution-id institution-id-type=\"FundRef\">http://dx.doi.org/10.13039/100000025</institution-id>
                        <institution>National Institute of Mental Health</institution>
                    </institution-wrap>
                </funding-source>
            <award-id>R01MH107333</award-id>
            <principal-award-recipient>
                <name><surname>Kim</surname><given-names>Woong-Ki</given-names></name>
            </principal-award-recipient>
        </award-group>
    </funding-group>""", None),
    ("""<funding-group specific-use=\"FundRef\">
            <award-group>
                <funding-source>
                    <institution-wrap>
                        <institution>Deutsche Forschungsgemeinschaft</institution>
                        <institution-id>http://search.crossref.org/fundref?q=501100001659</institution-id>
                    </institution-wrap>
                </funding-source>
                <award-id>Re 628/16-1</award-id>
                <award-id>GRK 1216</award-id>
            </award-group>
        </funding-group>""", None),
    ("""<funding-group>
            <award-group id=\"funding-1\">
                <funding-source>
                    <institution-wrap>
                        <institution>National Institutes of Health </institution>
                        <institution-id institution-id-type=\"open-funder-registry\">10.13039/100000002</institution-id>
                    </institution-wrap>
                </funding-source>
            </award-group>
        </funding-group>""", None),

    # handing <named-content>
    ("""<funding-group>
            <award-group>
                <funding-source>
                    <named-content content-type=\"funder-name\">Austrian Science Fund</named-content>
                    <named-content content-type=\"funder-identifier\">10.13039/501100002428</named-content>
                </funding-source>
                <award-id>P 27625</award-id>
            </award-group>
            <funding-statement>This work was supported by Austrian Science Fund [grant number P 27625].</funding-statement>
        </funding-group>""", None),

    # handling xlink:href attributes
    ("""<funding-group>
            <award-group>
                <funding-source xlink:href=\"http://dx.doi.org/10.13039/501100000269\">Economic and Social Research Council</funding-source>
                <award-id>RES-360-25-0032</award-id>
            </award-group>
            <award-group>
                <funding-source xlink:href=\"http://dx.doi.org/10.13039/100004440\">Wellcome Trust</funding-source>
                <award-id>106542/Z/14/Z</award-id>
            </award-group>
        </funding-group>""", None)
]

acknowledgement_tags_and_parsed_dicts = [
    # variants with <ack id> may/may not have a <title>. always have <p> but may/may not have <p id>.  <title> never has attributes.
    # the <p> text might contain <funding-source> or <ext-link> tags.
    #   the <ext-link> tags have required attributes 'ext-link-type' and 'xlink:href', and optional attribute 'id'.  all the <ext-links> are URLs.
    ("""<ack id=\"ack0005\">
            <title>Acknowledgements</title>
            <p>The authors thank the <funding-source id=\"gs0005\">BBSRC</funding-source> (Project Grants BB/M025349/1 and BB/P011969/1) for its continued support, and appreciate the helpful comments of Dr Rob Young, Cardiff University School of Optometry and Vision Sciences.</p>
        </ack>""", {
            'text': 'The authors thank the BBSRC (Project Grants BB/M025349/1 and BB/P011969/1) for its continued support, and appreciate the helpful comments of Dr Rob Young, Cardiff University School of Optometry and Vision Sciences.',
            'funding': [{'text': 'BBSRC', 'id': 'gs0005'}],
            'url': None}),
    ("""<ack id=\"S27\">
            <p>Supported by AA-11431 and AA-12908 from the National Institutes of Health and the Tobacco-Related Disease Research Program Grant 17RT-0171.</p>
        </ack>""", {
            'text': 'Supported by AA-11431 and AA-12908 from the National Institutes of Health and the Tobacco-Related Disease Research Program Grant 17RT-0171.',
            'funding': [],
            'url': None}),
    ("""<ack id=\"S11\">
            <title>Acknowledgements</title>
            <p id=\"P33\">This work was supported by the National Institutes of Health,National Cancer Institute grants R01CA196967 and R01CA209886.</p>
        </ack>""", {
            'text': 'This work was supported by the National Institutes of Health,National Cancer Institute grants R01CA196967 and R01CA209886.',
            'funding': [],
            'url': None}),
    ("""<ack id=\"mee312535-sec-0015\">
            <title>Data accessibility</title>
            <p>The data used is included in the RepeatABEL package available at <ext-link ext-link-type=\"uri\" xlink:href=\"https://cran.r-project.org/web/packages/RepeatABEL\">https://cran.r-project.org/web/packages/RepeatABEL</ext-link>.</p>
        </ack>""", {
            'text': 'The data used is included in the RepeatABEL package available at https://cran.r-project.org/web/packages/RepeatABEL.',
            'funding': [],
            'url': 'https://cran.r-project.org/web/packages/RepeatABEL'}),
    # variants with <ack> are similar to the above.
    ("""<ack>
            <title>Acknowledgments</title>
            <p>D.B.K. thanks Prof. Nigel Harper for a very useful discussion. We also thank the referees and the journal editors for exceptionally careful and thoughtful reviews that helped improve the manuscript considerably.</p>
        </ack>""", {
            'text': 'D.B.K. thanks Prof. Nigel Harper for a very useful discussion. We also thank the referees and the journal editors for exceptionally careful and thoughtful reviews that helped improve the manuscript considerably.',
            'funding': [],
            'url': None}),
    ("""<ack>
            <title>Conflict of interest</title>
            <p>The authors declare there is no conflict of interest associated with this manuscript.</p>
        </ack>""", {
            'text': 'The authors declare there is no conflict of interest associated with this manuscript.',
            'funding': [],
            'url': None})
]

affiliation_tags_and_parsed_dicts = [
    # mix of <aff> tags with and without IDs
    ("""<aff>Department of Internal Medicine, Division of Cardiology, Inha University Hospital, Incheon, South Korea</aff>""", None),
    ("""<aff id=\"aff1\"><label>1</label>Department of Cardiology, Atatürk Chest Diseases and Chest Surgery Training and Research Hospital; Ankara-Turkey</aff>""", None),
    # there can exist a <label> tag with/without IDs
    ("""<aff><label>3</label>Center for Medical Education, Sapporo Medical University, <addr-line>Sapporo, Japan</addr-line></aff>""", None),
    # sometimes, the marker used in paper is kept also.  for example, `1` in superscript.
    # this can exist with/without the <label> tag.  as in, it's inconsistent whether the marker is encapsulated in <label> or kept as string
    ("""<aff id=\"I1\">\n<sup>1</sup>Department of Orthodontics, College of Dentistry, King Khalid University, Abha, Saudi Arabia</aff>""", None),
    ("""<aff id=\"hic312304-aff-0001\"><label><sup>1</sup></label><institution>University of Dundee</institution></aff>""", None),
    # <institution> tags can be straightforward; just ignore and grab text
    ("""<aff id=\"AF02477-1\"><label>1</label><institution>School of Chemistry, The University of Manchester, Manchester, United Kingdom</institution>""", None),
    # sometimes <institution> tags can have SIBLING tags, like <addr-line> or <country>
    ("""<aff id=\"aff002\"><label>2</label>Sr. Consultant &amp; Head, Dept. of Neurology, <institution>National Neurosciences Centre, Peerless Hospital</institution>, <addr-line>Kolkata, India</addr-line></aff>""", None),
    ("""<aff id=\"aff2\"><label><sup>2</sup></label>Institute for Transplantation Diagnostics and Cell Therapeutics, <institution>Heinrich Heine University Düsseldorf</institution>, Düsseldorf, <country>Germany</country>.</aff>""", None),
    # <named-content> is also a common CHILD tag; these can be either entirely structured affiliation entries  (not intended for tag.text)
    ("""<aff id=\"embr201642857-aff-0007\">
            <label><sup>7</sup></label>
            <institution>VIB</institution>
            <named-content content-type=\"city\">Zwijnaarde</named-content>
            <country country=\"BE\">Belgium</country>
        </aff>""", None),
    # or overlayed over a single affiliation string (comma-sep if call tag.text)
    ("""<aff id=\"AFF0005\">
            <label><sup>e</sup></label>
            <institution>
                <named-content content-type=\"department\">School of Public Health &amp; Health Systems</named-content>, <named-content content-type=\"institution-name\">University of Waterloo</named-content>
            </institution>
        </aff>""", None),
    # example of a nonsense one that has TWO <named-content> tags, whitespaces, the <sup> tag WITHIN <label>
    ("""<aff id=\"ejn14074-aff-0007\">\n
        <label><sup>7</sup></label>\n
        <named-content content-type=\"organisation-division\">Brain Research Institute</named-content>\n
        <institution>University of Zürich</institution>\n
        <named-content content-type=\"city\">Zürich</named-content>\n
        <country country=\"CH\">Switzerland</country>\n</aff>""", None),
    # most common content-type within <named-content> are: 'department', 'organisation-division', 'city', 'institution-name', 'postal-code', 'country-part', etc.

    # <institution-wrap> is the other popular way to surface <institution> tags.
    # They seem to always come with 1+ <institution-id> as children.

    # finally, these wrappers can wrap multiple <institution> tags.
    # in this example, see how the COMMA is awkwardly encapsulated within <institution> tags?  Also, notice how the country is untagged outside of <institution-wrap>
    # basically, everything is weird.
    ("""<aff id=\"Aff10\">
        <label>10</label>
        <institution-wrap>
            <institution-id institution-id-type=\"ISNI\">0000000123222966</institution-id>
            <institution-id institution-id-type=\"GRID\">grid.6936.a</institution-id>
            <institution>Institute of Experimental Genetics, Life and Food Science Center Weihenstephan, </institution>
            <institution>Technische Universität München, </institution>
        </institution-wrap>Freising-Weihenstephan, Germany </aff>""", None)
]

author_tags_and_parsed_dicts = [
    # every author seems to be in a <contrib> tag.
    # all <contrib> tags seem to have a 'contrib-type' attribute, which often equals 'author' and sometimes equals 'collab'

    # below is an 'author' that has <name>, <address>, and <bio> child tags.  Also XREF to affiliation (can have multiple).
    ("""<contrib contrib-type=\"author\">
            <name><surname>Sandström</surname><given-names>Annica</given-names></name>
            <address><email>annica.sandstrom@ltu.se</email></address>
            <xref ref-type=\"aff\" rid=\"Aff2\"/>
            <bio><sec id=\"d30e226\"><title>Annica Sandström</title><p>is an Associate Professor in Political Science at Luleå University of Technology. Working foremost within the field of environmental policy and management, her publications include empirical studies on the socio-political complexities of natural resource governance as well as theory-driven pieces on collaborative management, adaptive management, and policy networks.</p></sec></bio>
        </contrib>""", None),
    ("""<contrib contrib-type="author">
            <name><surname>Cassidy</surname><given-names>John W.</given-names></name>
            <xref ref-type="aff" rid="A1">1</xref>
            <xref ref-type="aff" rid="A2">2</xref>
        </contrib>""", None),

    # below is an 'author' that contains a <collab> child tag.  We can see sometimes there's other tags like an XREF to affiliation which can probably be .decomposed()
    ("""<contrib contrib-type=\"author\">
            <collab>The HIV Neurobehavioral Research Programs (HNRP) Group</collab>
        </contrib>""", None),
    ("""<contrib contrib-type=\"author\">
            <collab>JET EFDA contributors</collab>
            <xref ref-type=\"aff\" rid=\"aff1\">a</xref><xref ref-type=\"fn\" rid=\"fn3\">3</xref>
        </contrib>""", None),

    # below is a 'collab' that also contains nested <contrib> tags wrapped by <contrib-group>.  Yikes!
    # luckily, it seems <contrib-group> is rare and always nested within an ultimate parent <contrib>
    # --> these are more like affiliations
    ("""<contrib contrib-type=\"collab\">
            <collab>UK Biobank Eye and Vision Consortium\n
                <contrib-group>
                    <contrib contrib-type=\"collab\">
                        <name><surname>Aslam</surname><given-names>Tariq</given-names></name>
                    </contrib>
                    <contrib contrib-type=\"collab\">
                        <name><surname>Bishop</surname><given-names>Paul</given-names></name>
                    </contrib>
                    <contrib contrib-type=\"collab\">
                        <name><surname>Barman</surname><given-names>Sarah</given-names></name>
                    </contrib>
                </contrib-group>
            </collab>
        </contrib>
    """, None),
    ("""<contrib contrib-type="author">
            <collab>WERF EPHect Working Group
                <contrib-group>
                    <contrib contrib-type="author"><name><surname>Adamson</surname><given-names>G.D.</given-names></name></contrib>
                    <contrib contrib-type="author"><name><surname>Allaire</surname><given-names>C.</given-names></name></contrib>
                </contrib-group>
            </collab>
        </contrib>""", None),

    # there are optional <aff> tags instead of an <xref ref-type=\"aff\">
    ("""<contrib contrib-type=\"author\">
            <name><surname>Beedle</surname><given-names>Aaron M</given-names></name>
            <aff id=\"A1\">Department of Pharmaceutical and Biomedical Sciences, University of Georgia College of Pharmacy, Athens, GA 30602 USA</aff>
        </contrib>""", None),

    # corresponding authors are indicated in two ways: (i) within <contrib> as a 'corresp=yes' attribute, (ii) within <xref> as a 'ref-type=corresp' attribute
    ("""<contrib contrib-type=\"author\" corresp=\"yes\">
            <name><surname>Kim</surname><given-names>Woong-Ki</given-names></name>
            <address><email>kimw@evms.edu</email></address>
            <xref ref-type=\"aff\" rid=\"Aff1\">1</xref>
        </contrib>""", None),
    ("""<contrib contrib-type=\"author\">
            <name><surname>Suero Molina</surname><given-names>Eric</given-names></name>
            <degrees>MD, MBA</degrees>
            <!--<email>eric.suero@ukmuenster.de</email>-->
            <xref ref-type=\"aff\" rid=\"aff1\"/>
            <xref ref-type=\"corresp\" rid=\"cor1\"/>
        </contrib>""", None),
    # note that contrib-type 'editor' is also present, and seems to accompany <role> tag and 'corresp=no' attribute
    ("""<contrib contrib-type=\"editor\" corresp=\"no\">
            <name><surname>Greene</surname><given-names>Robert L.</given-names></name>
            <role>Editor</role>
        </contrib>""", None),

    # within <contrib> are optional child tags <contrib-id>
    # the 'contrib-id-type' seems to always be 'orcid'
    # authentication seems optional
    ("""<contrib contrib-type=\"author\" corresp=\"yes\">
            <contrib-id authenticated=\"false\" contrib-id-type=\"orcid\">https://orcid.org/0000-0002-9987-6824</contrib-id>
            <name><surname>Sandeepa</surname><given-names>N. C.</given-names></name>
            <email>drsandeepanc@gmail.com</email>
            <xref ref-type=\"aff\" rid=\"I2\">\n<sup>2</sup>\n</xref>
        </contrib>""", None),
    ("""<contrib contrib-type=\"author\" corresp=\"yes\">
            <contrib-id contrib-id-type=\"orcid\">http://orcid.org/0000-0003-1079-4775</contrib-id>
            <name><surname>West</surname><given-names>Ann H.</given-names></name>
            <address><email>awest@ou.edu</email></address>
            <xref ref-type=\"aff\" rid=\"Aff1\">1</xref>
        </contrib>""", None),

    # more edge cases; a <contrib> tag with no <name> --> probably just remove
    ("""<contrib contrib-type="author">
            <collab>on behalf of the National Advisory Committee on Blood and Blood Products
                <xref ref-type="author-notes" rid="fn1">*</xref>
            </collab>
        </contrib>""", None),

]