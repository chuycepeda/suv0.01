/* Submit from with AJAX using Materialized CSS elements
Must haves:
- Materialized Framework
- Jquery before makeMeAJAX is called
- All inputs must be inside target form
*/

function makeMeAJAX(url,httpType,targetForm,btn){
    //If submit btn is disable return and dont do AJAX on click
    if (btn.hasClass('disabled')) return false;
    //Add disable class
    btn.addClass('disabled');
    //Get all input values from form
    var data={};
    $("form#"+targetForm+" :input").each(function(){
        if ($(this).attr('name')) data[$(this).attr('name')]=$(this).val();
    });
    //Do AJAX on URL
    $.ajax({
        type: httpType,
        url: url,
        data: data,
    }).done(function( result ) {
        btn.removeClass('disabled');
        var _msg = '<span class="brand-color-text">'+result.response+'</span>';
        Materialize.toast(_msg, 3500);
        console.log(result);
    }).fail(function( error ) {
        btn.removeClass('disabled');
        var _msg = 'Code: '+error.status+' Response: '+error.statusText;
        Materialize.toast(_msg, 3500);
        console.log(error);    
    });
}